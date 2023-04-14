pragma solidity ^0.8.0;

import "./interfaces/IKeyManager.sol";
import "./abstract/SchnorrSECP256K1.sol";
import "./abstract/Shared.sol";

/**
 * @title    KeyManager contract
 * @notice   Holds the aggregate and governance keys, functions to update them,
 *           and consumeKeyNonce so other contracts can verify signatures and updates _lastValidateTime
 */
contract KeyManager is SchnorrSECP256K1, Shared, IKeyManager {
    uint256 private constant _AGG_KEY_TIMEOUT = 2 days;

    /// @dev    The current (schnorr) aggregate key.
    Key private _aggKey;
    /// @dev    The current governance key.
    address private _govKey;
    /// @dev    The current community key.
    address private _commKey;
    /// @dev    The last time that a sig was verified (used for a dead man's switch)
    uint256 private _lastValidateTime;
    mapping(uint256 => bool) private _isNonceUsedByAggKey;

    constructor(
        Key memory initialAggKey,
        address initialGovKey,
        address initialCommKey
    ) nzAddr(initialGovKey) nzAddr(initialCommKey) nzKey(initialAggKey) validAggKey(initialAggKey) {
        _aggKey = initialAggKey;
        _govKey = initialGovKey;
        _commKey = initialCommKey;
        _lastValidateTime = block.timestamp;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Checks the validity of a signature and msgHash, then updates _lastValidateTime
     * @dev     It would be nice to split this up, but these checks
     *          need to be made atomicly always. This needs to be available
     *          in this contract and in the Vault etc
     * @param sigData   The keccak256 hash over the msg (uint256).
     * @param msgHash   The hash of the message being signed. The hash of the function
     *                  call parameters is concatenated and hashed together with the nonce, the
     *                  address of the caller, the chainId, and the address of this contract.
     */
    function _consumeKeyNonce(SigData calldata sigData, bytes32 msgHash) internal {
        Key memory key = _aggKey;

        require(
            verifySignature(uint256(msgHash), sigData.sig, key.pubKeyX, key.pubKeyYParity, sigData.kTimesGAddress),
            "KeyManager: Sig invalid"
        );
        require(!_isNonceUsedByAggKey[sigData.nonce], "KeyManager: nonce already used");

        _lastValidateTime = block.timestamp;
        _isNonceUsedByAggKey[sigData.nonce] = true;

        // Disable because tx.origin is not being used in the logic
        // solhint-disable-next-line avoid-tx-origin
        emit SignatureAccepted(sigData, tx.origin);
    }

    /**
     * @notice  Concatenates the contractMsgHashed with the nonce, the address of the caller,
     *          the chainId, and the address of this contract, then hashes that and verifies the
     *          signature. This is done to prevent replay attacks.
     * @param sigData   The keccak256 hash over the msg (uint256).
     * @param contractMsgHash   The hash of the function's call parameters. This will be hashed
     *                  over other parameters to prevent replay attacks.
     */
    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) external override {
        bytes32 msgHash = keccak256(
            abi.encode(contractMsgHash, sigData.nonce, msg.sender, block.chainid, address(this))
        );
        _consumeKeyNonce(sigData, msgHash);
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current aggregate key
     * @param sigData   The keccak256 hash over the msg (uint256) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint256)
     * @param newAggKey The new aggregate key to be set. The x component of the pubkey (uint256),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithAggKey(
        SigData calldata sigData,
        Key calldata newAggKey
    )
        external
        override
        nzKey(newAggKey)
        validAggKey(newAggKey)
        consumeKeyNonceKeyManager(sigData, keccak256(abi.encode(this.setAggKeyWithAggKey.selector, newAggKey)))
    {
        emit AggKeySetByAggKey(_aggKey, newAggKey);
        _aggKey = newAggKey;
    }

    /**
     * @notice  Set a new aggregate key. Can only be called by the current governance key
     * @param newAggKey The new aggregate key to be set. The x component of the pubkey (uint256),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithGovKey(
        Key calldata newAggKey
    ) external override nzKey(newAggKey) validAggKey(newAggKey) timeoutEmergency onlyGovernor {
        emit AggKeySetByGovKey(_aggKey, newAggKey);
        _aggKey = newAggKey;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current aggregate key
     * @param sigData   The keccak256 hash over the msg (uint256) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint256)
     * @param newGovKey The new governance key to be set.

     */
    function setGovKeyWithAggKey(
        SigData calldata sigData,
        address newGovKey
    )
        external
        override
        nzAddr(newGovKey)
        consumeKeyNonceKeyManager(sigData, keccak256(abi.encode(this.setGovKeyWithAggKey.selector, newGovKey)))
    {
        emit GovKeySetByAggKey(_govKey, newGovKey);
        _govKey = newGovKey;
    }

    /**
     * @notice  Set a new governance key. Can only be called by current governance key
     * @param newGovKey    The new governance key to be set.
     */
    function setGovKeyWithGovKey(address newGovKey) external override nzAddr(newGovKey) onlyGovernor {
        emit GovKeySetByGovKey(_govKey, newGovKey);
        _govKey = newGovKey;
    }

    /**
     * @notice  Set a new community key. Requires a signature from the current aggregate key
     * @param sigData   The keccak256 hash over the msg (uint256) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint256)
     * @param newCommKey The new community key to be set.

     */
    function setCommKeyWithAggKey(
        SigData calldata sigData,
        address newCommKey
    )
        external
        override
        nzAddr(newCommKey)
        consumeKeyNonceKeyManager(sigData, keccak256(abi.encode(this.setCommKeyWithAggKey.selector, newCommKey)))
    {
        emit CommKeySetByAggKey(_commKey, newCommKey);
        _commKey = newCommKey;
    }

    /**
     * @notice  Update the Community Key. Can only be called by the current Community Key.
     * @param newCommKey   New Community key address.
     */
    function setCommKeyWithCommKey(address newCommKey) external override onlyCommunityKey nzAddr(newCommKey) {
        emit CommKeySetByCommKey(_commKey, newCommKey);
        _commKey = newCommKey;
    }

    /**
     * @notice Withdraw any native tokens on this contract. The intended execution of this contract doesn't
     * require any native tokens. This function is just to recover any tokens that might have been sent to
     * this contract by accident (or any other reason).
     */
    function govWithdrawNative() external override onlyGovernor {
        uint256 amount = address(this).balance;

        // Could use msg.sender but hardcoding the get call just for extra safety
        address recipient = _getGovernanceKey();
        payable(recipient).transfer(amount);
    }

    /**
     * @notice Emit an event containing an action message. Can only be called by the governor.
     */
    function govAction(bytes32 message) external override onlyGovernor {
        emit GovernanceAction(message);
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
        return _aggKey;
    }

    /**
     * @notice  Get the current governance key
     * @return  The Key struct for the governance key
     */
    function getGovernanceKey() external view override returns (address) {
        return _getGovernanceKey();
    }

    /**
     * @notice  Get the current community key
     * @return  The Key struct for the community key
     */
    function getCommunityKey() external view override returns (address) {
        return _getCommunityKey();
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
     *  @notice Allows this contract to receive native
     */
    receive() external payable {}

    /**
     * @notice  Get the current governance key
     * @return  The Key struct for the governance key
     */
    function _getGovernanceKey() internal view returns (address) {
        return _govKey;
    }

    /**
     * @notice  Get the current community key
     * @return  The Key struct for the community key
     */
    function _getCommunityKey() internal view returns (address) {
        return _commKey;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that enough time has passed for setAggKeyWithGovKey. Needs
    ///         to be done as a modifier so that it can happen before consumeKeyNonce
    modifier timeoutEmergency() {
        require(block.timestamp - _lastValidateTime >= _AGG_KEY_TIMEOUT, "KeyManager: not enough time");
        _;
    }

    /// @dev    Check that an aggregate key is capable of having its signatures
    ///         verified by the schnorr lib.
    modifier validAggKey(Key memory key) {
        verifySigningKeyX(key.pubKeyX);
        _;
    }

    /// @dev    Check that the sender is the governance address
    modifier onlyGovernor() {
        require(msg.sender == _getGovernanceKey(), "KeyManager: not governor");
        _;
    }

    /// @dev    Check that the caller is the Community Key address.
    modifier onlyCommunityKey() {
        require(msg.sender == _getCommunityKey(), "KeyManager: not Community Key");
        _;
    }

    /// @dev    For functions in this contract that require a signature from the aggregate key
    //          the msg.sender can't be hashed as anyone can make the call. Instead the
    //          address of this contract is used as the sender and hashed in the message.
    modifier consumeKeyNonceKeyManager(SigData calldata sigData, bytes32 contractMsgHash) {
        bytes32 msgHash = keccak256(
            abi.encode(contractMsgHash, sigData.nonce, address(this), block.chainid, address(this))
        );
        _consumeKeyNonce(sigData, msgHash);
        _;
    }
}
