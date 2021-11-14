pragma solidity ^0.8.0;


import "./interfaces/IKeyManager.sol";
import "./abstract/SchnorrSECP256K1.sol";
import "./abstract/Shared.sol";


/**
* @title    KeyManager contract
* @notice   Holds the aggregate and governance keys, functions to update them,
*           and isUpdatedValidSig so other contracts can verify signatures and updates _lastValidateTime
* @author   Quantaf1re (James Key)
*/
contract KeyManager is SchnorrSECP256K1, Shared, IKeyManager {

    uint constant private _AGG_KEY_TIMEOUT = 2 days;

    /// @dev    Used to get the key with the keyID. This prevents isUpdatedValidSig being called
    ///         by keys that aren't the aggKey or govKey, which prevents outsiders being
    ///         able to change _lastValidateTime
    mapping(KeyID => Key) private _keyIDToKey;
    /// @dev    The last time that a sig was verified (used for a dead man's switch)
    uint private _lastValidateTime;
    mapping(KeyID => mapping(uint => bool)) private _keyToNoncesUsed;
    // The chainID of the current chain being used, to check in sigs to prevent replay
    // attacks across different EVM chains
    uint public immutable CHAIN_ID;


    event AggKeySetByAggKey(Key oldKey, Key newKey);
    event AggKeySetByGovKey(Key oldKey, Key newKey);
    event GovKeySetByGovKey(Key oldKey, Key newKey);


    constructor(Key memory aggKey, Key memory govKey, uint chainID) {
        _keyIDToKey[KeyID.AGG] = aggKey;
        _keyIDToKey[KeyID.GOV] = govKey;
        _lastValidateTime = block.timestamp;
        CHAIN_ID = chainID;
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Checks the validity of a signature and msgHash, then updates _lastValidateTime.
     *          This also saved the nonce used so that it, and therefore the sig over it, can't
     *          be used again
     * @dev     It would be nice to split this up, but these checks
     *          need to be made atomicly always. This needs to be available
     *          in this contract and in the Vault etc
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData)
     *                  from the current aggregate key (uint)
     * @param contractMsgHash   The hash of the thing being signed but generated by the contract
     *                  to check it against the hash in sigData (bytes32) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData)
     * @param keyID     The KeyID that indicates which key to verify the sig with. Ensures that
     *                  only 'registered' keys can be used to successfully call this fcn and change
     *                  _lastValidateTime
     * @return          Bool used by caller to be absolutely sure that the function hasn't reverted
     */
    function isUpdatedValidSig(
        SigData calldata sigData,
        bytes32 contractMsgHash,
        KeyID keyID
    ) public override returns (bool) {
        Key memory key = _keyIDToKey[keyID];
        // We require the msgHash param in the sigData is equal to the contract
        // message hash (the rules coded into the contract)
        require(sigData.msgHash == uint(contractMsgHash), "KeyManager: invalid msgHash");
        require(
            verifySignature(
                sigData.msgHash,
                sigData.sig,
                key.pubKeyX,
                key.pubKeyYParity,
                sigData.kTimesGAddr
            ),
            "KeyManager: Sig invalid"
        );
        require(!_keyToNoncesUsed[keyID][sigData.nonce], "KeyManager: nonce already used");
        require(sigData.keyManAddr == address(this), "KeyManager: wrong keyManAddr");
        require(sigData.chainID == CHAIN_ID, "KeyManager: wrong chainID");

        _lastValidateTime = block.timestamp;
        _keyToNoncesUsed[keyID][sigData.nonce] = true;

        return true;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current aggregate key
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint)
     * @param newKey    The new aggregate key to be set. The x component of the pubkey (uint),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithAggKey(
        SigData calldata sigData,
        Key calldata newKey
    ) external override nzKey(newKey) refundGas updatedValidSig(
        sigData,
        keccak256(abi.encodeWithSelector(
            this.setAggKeyWithAggKey.selector,
            SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
            newKey
        )),
        KeyID.AGG
    ) {
        emit AggKeySetByAggKey(_keyIDToKey[KeyID.AGG], newKey);
        _keyIDToKey[KeyID.AGG] = newKey;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current governance key
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current governance key (uint)
     * @param newKey    The new aggregate key to be set. The x component of the pubkey (uint),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithGovKey(
        SigData calldata sigData,
        Key calldata newKey
    ) external override nzKey(newKey) validTime updatedValidSig(
        sigData,
        keccak256(abi.encodeWithSelector(
            this.setAggKeyWithGovKey.selector,
            SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
            newKey
        )),
        KeyID.GOV
    ) {
        emit AggKeySetByGovKey(_keyIDToKey[KeyID.AGG], newKey);
        _keyIDToKey[KeyID.AGG] = newKey;
    }

    /**
     * @notice  Set a new governance key. Requires a signature from the current governance key
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current governance key (uint)
     * @param newKey    The new governance key to be set. The x component of the pubkey (uint),
     *                  the parity of the y component (uint8)
     */
    function setGovKeyWithGovKey(
        SigData calldata sigData,
        Key calldata newKey
    ) external override nzKey(newKey) updatedValidSig(
        sigData,
        keccak256(abi.encodeWithSelector(
            this.setGovKeyWithGovKey.selector,
            SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
            newKey
        )),
        KeyID.GOV
    ) {
        emit GovKeySetByGovKey(_keyIDToKey[KeyID.GOV], newKey);
        _keyIDToKey[KeyID.GOV] = newKey;
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
    function getAggregateKey() external override view returns (Key memory) {
        return (_keyIDToKey[KeyID.AGG]);
    }

    /**
     * @notice  Get the current governance key
     * @return  The Key struct for the governance key
     */
    function getGovernanceKey() external override view returns (Key memory) {
        return (_keyIDToKey[KeyID.GOV]);
    }

    /**
     * @notice  Get the last time that a function was called which
     *          required a signature from _aggregateKeyData or _governanceKeyData
     * @return  The last time isUpdatedValidSig was called, in unix time (uint)
     */
    function getLastValidateTime() external override view returns (uint) {
        return _lastValidateTime;
    }

    /**
     * @notice  Get whether or not the specific keyID has used this nonce before
     *          since it cannot be used again
     * @return  Whether the nonce has already been used (bool)
     */
    function isNonceUsedByKey(KeyID keyID, uint nonce) external override view returns (bool) {
        return _keyToNoncesUsed[keyID][nonce];
    }

    /**
     *  @notice Allows this contract to receive ETH used to refund callers
     */
    receive () external payable {}



    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that enough time has passed for setAggKeyWithGovKey. Needs
    ///         to be done as a modifier so that it can happen before updatedValidSig
    modifier validTime() {
        require(block.timestamp - _lastValidateTime >= _AGG_KEY_TIMEOUT, "KeyManager: not enough delay");
        _;
    }

    /// @dev    Call isUpdatedValidSig
    modifier updatedValidSig(
        SigData calldata sigData,
        bytes32 contractMsgHash,
        KeyID keyID
    ) {
        require(isUpdatedValidSig(sigData, contractMsgHash, keyID));
        _;
    }
}
