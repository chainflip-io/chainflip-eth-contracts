pragma solidity ^0.8.0;

import "./interfaces/IKeyManager.sol";
import "./abstract/SchnorrSECP256K1.sol";
import "./abstract/Shared.sol";

/**
 * @title    KeyManager contract
 * @notice   Holds the aggregate and governance keys, functions to update them,
 *           and consumeKeyNonce so other contracts can verify signatures and updates _lastValidateTime
 * @author   Quantaf1re (James Key)
 */
contract KeyManager is SchnorrSECP256K1, Shared, IKeyManager {
    uint256 private constant _AGG_KEY_TIMEOUT = 2 days;

    /// @dev    The current (schnorr) aggregate key.
    Key public aggKey;
    /// @dev    The current governance key.
    address public govKey;
    /// @dev    The last time that a sig was verified (used for a dead man's switch)
    uint256 private _lastValidateTime;
    mapping(uint256 => bool) private _isNonceUsedByAggKey;
    /// @dev    Whitelist for who can call isValidSig
    mapping(address => bool) private _canConsumeNonce;
    bool private _canConsumeNonceSet;
    uint256 private _numberWhitelistedAddresses;

    constructor(Key memory _aggKey, address _govKey) validAggKey(_aggKey) {
        aggKey = _aggKey;
        govKey = _govKey;
        _lastValidateTime = block.timestamp;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Sets the specific addresses that can call isValidSig. This
     *          function can only ever be called once! Yes, it's possible to
     *          frontrun this, but honestly, it's fine in practice - it just
     *          needs to be set up successfully once, which is trivial
     * @param addrs   The addresses to whitelist
     */
    function setCanConsumeNonce(address[] calldata addrs) external {
        require(!_canConsumeNonceSet, "KeyManager: already set");
        _canConsumeNonceSet = true;

        for (uint256 i = 0; i < addrs.length; i++) {
            // Avoid duplicated newAddrs. Otherwise we could brick the updateCanConsumeNonce
            // since it relies on the _numberWhitelistedAddresses and it has this check
            require(_canConsumeNonce[addrs[i]] == false, "KeyManager: address already whitelisted");
            _canConsumeNonce[addrs[i]] = true;
        }

        // To make sure we never brick this contract
        require(_canConsumeNonce[address(this)], "KeyManager: KeyManager not whitelisted");

        _numberWhitelistedAddresses = addrs.length;
    }

    /**
     * @notice  Replaces the specific addresses that can call isValidSig. To be used if
     *          contracts are updated. Can delist addresses and can add an arbitrary number of new addresses.
     * @param currentAddrs   List of current whitelisted addresses
     * @param newAddrs   List of new addresses to whitelist
     */
    function updateCanConsumeNonce(
        SigData calldata sigData,
        address[] calldata currentAddrs,
        address[] calldata newAddrs
    )
        external
        consumerKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.updateCanConsumeNonce.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    currentAddrs,
                    newAddrs
                )
            )
        )
    {
        require(currentAddrs.length == _numberWhitelistedAddresses, "KeyManager: array incorrect length");

        // Remove current whitelisted addresses
        for (uint256 i = 0; i < currentAddrs.length; i++) {
            require(_canConsumeNonce[currentAddrs[i]], "KeyManager: cannot dewhitelist");
            _canConsumeNonce[currentAddrs[i]] = false;
        }

        //  Whitelist any number of new addresses
        for (uint256 i = 0; i < newAddrs.length; i++) {
            // Avoid duplicated newAddrs
            require(!_canConsumeNonce[newAddrs[i]], "KeyManager: address already whitelisted");
            _canConsumeNonce[newAddrs[i]] = true;
        }

        // To make sure we never brick this contract
        require(_canConsumeNonce[address(this)], "KeyManager: KeyManager not whitelisted");

        _numberWhitelistedAddresses = newAddrs.length;
    }

    /**
     * @notice  Checks the validity of a signature and msgHash, then updates _lastValidateTime
     * @dev     It would be nice to split this up, but these checks
     *          need to be made atomicly always. This needs to be available
     *          in this contract and in the Vault etc
     * @param sigData   The keccak256 hash over the msg (uint256) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData)
     *                  from the current aggregate key (uint256)
     * @param contractMsgHash   The hash of the thing being signed but generated by the contract
     *                  to check it against the hash in sigData (bytes32) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData)
     * @return          Bool used by caller to be absolutely sure that the function hasn't reverted
     */
    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) public override returns (bool) {
        require(_canConsumeNonce[msg.sender], "KeyManager: not whitelisted");
        Key memory key = aggKey;
        // We require the msgHash param in the sigData is equal to the contract
        // message hash (the rules coded into the contract)
        require(sigData.msgHash == uint256(contractMsgHash), "KeyManager: invalid msgHash");
        require(
            verifySignature(sigData.msgHash, sigData.sig, key.pubKeyX, key.pubKeyYParity, sigData.kTimesGAddr),
            "KeyManager: Sig invalid"
        );
        require(!_isNonceUsedByAggKey[sigData.nonce], "KeyManager: nonce already used");
        require(sigData.keyManAddr == address(this), "KeyManager: wrong keyManAddr");
        require(sigData.chainID == block.chainid, "KeyManager: wrong chainID");

        _lastValidateTime = block.timestamp;
        _isNonceUsedByAggKey[sigData.nonce] = true;

        // Disable because tx.origin is not being used in the logic
        // solhint-disable-next-line avoid-tx-origin
        emit SignatureAccepted(sigData, tx.origin);

        return true;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current aggregate key
     * @param sigData   The keccak256 hash over the msg (uint256) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint256)
     * @param newKey    The new aggregate key to be set. The x component of the pubkey (uint256),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithAggKey(SigData calldata sigData, Key calldata newKey)
        external
        override
        nzKey(newKey)
        validAggKey(newKey)
        consumerKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.setAggKeyWithAggKey.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    newKey
                )
            )
        )
    {
        emit AggKeySetByAggKey(aggKey, newKey);
        aggKey = newKey;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current governance key
     * @param newKey    The new aggregate key to be set. The x component of the pubkey (uint256),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithGovKey(Key calldata newKey) external override nzKey(newKey) validTime isGovernor {
        emit AggKeySetByGovKey(aggKey, newKey);
        aggKey = newKey;
    }

    /**
     * @notice  Set a new governance key. Requires a signature from the current governance key
     * @param newKey    The new governance key to be set. The x component of the pubkey (uint256),
     *                  the parity of the y component (uint8)
     */
    function setGovKeyWithGovKey(address newKey) external override nzAddr(newKey) isGovernor {
        emit GovKeySetByGovKey(govKey, newKey);
        govKey = newKey;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the current aggregate key
     * @return  The Key struct for the aggregate key
     */
    function getAggregateKey() external view override returns (Key memory) {
        return aggKey;
    }

    /**
     * @notice  Get the current governance key
     * @return  The Key struct for the governance key
     */
    function getGovernanceKey() external view override returns (address) {
        return govKey;
    }

    /**
     * @notice  Get the last time that a function was called which
     *          required a signature from _aggregateKeyData or _governanceKeyData
     * @return  The last time consumeKeyNonce was called, in unix time (uint256)
     */
    function getLastValidateTime() external view override returns (uint256) {
        return _lastValidateTime;
    }

    /**
     * @notice  Get whether or not the specific keyID has used this nonce before
     *          since it cannot be used again
     * @return  Whether the nonce has already been used (bool)
     */
    function isNonceUsedByAggKey(uint256 nonce) external view override returns (bool) {
        return _isNonceUsedByAggKey[nonce];
    }

    /**
     * @notice  Get whether addr is whitelisted for validating a sig
     * @param addr  The address to check
     * @return  Whether or not addr is whitelisted or not
     */
    function canConsumeNonce(address addr) external view override returns (bool) {
        return _canConsumeNonce[addr];
    }

    /**
     * @notice  Get whether or not _canConsumeNonce has already been set, which
     *          prevents it from being set again
     * @return  The value of _canConsumeNonceSet
     */
    function canConsumeNonceSet() external view override returns (bool) {
        return _canConsumeNonceSet;
    }

    /**
     * @notice  Get number of whitelisted addresses
     * @return  The value of _numberWhitelistedAddresses
     */
    function getNumberWhitelistedAddresses() external view override returns (uint256) {
        return _numberWhitelistedAddresses;
    }

    /**
     *  @notice Allows this contract to receive ETH used to refund callers
     */
    receive() external payable {}

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that enough time has passed for setAggKeyWithGovKey. Needs
    ///         to be done as a modifier so that it can happen before consumeKeyNonce
    modifier validTime() {
        require(block.timestamp - _lastValidateTime >= _AGG_KEY_TIMEOUT, "KeyManager: not enough delay");
        _;
    }

    /// @dev    Check that an aggregate key is capable of having its signatures
    ///         verified by the schnorr lib.
    modifier validAggKey(Key memory key) {
        verifySigningKeyX(key.pubKeyX);
        _;
    }

    modifier isGovernor() {
        require(msg.sender == this.getGovernanceKey(), "KeyManager: not governor");
        _;
    }

    /// @dev    Call consumeKeyNonce
    modifier consumerKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) {
        // Need to make this an external call so that the msg.sender is the
        // address of this contract, otherwise calling setAggKeyWithAggKey
        // from any address would fail the whitelist check

        require(this.consumeKeyNonce(sigData, contractMsgHash));
        _;
    }
}
