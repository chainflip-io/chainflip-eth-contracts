pragma solidity ^0.7.0;
pragma abicoder v2;


import "./interfaces/IKeyManager.sol";
import "./abstract/SchnorrSECP256K1.sol";
import "./abstract/Shared.sol";


/**
* @title    KeyManager contract
* @notice   Holds the aggregate and governance keys, functions to update them, 
            and isValidSig so other contracts can verify signatures and updates _lastValidateTime
* @author   Quantaf1re (James Key)
*/
contract KeyManager is SchnorrSECP256K1, Shared, IKeyManager {

    /// @dev The aggregate key data used by ETH vault nodes to sign transfers
    Key private _aggKey;
    /// @dev The governance key data of the current governance quorum
    Key private _govKey;
    /// @dev The last time that a sig was verified (used for a dead man's switch)
    uint private _lastValidateTime;
    // Can't enable this line because the compiler errors
    // with "Constants of non-value type not yet implemented."
    // SigData private constant _NULL_SIG_DATA = SigData(0, 0);


    event KeyChange(
        bool signedByAggKey,
        Key oldKey,
        Key newKey
    );


    constructor(Key memory aggKey, Key memory govKey) {
        _aggKey = aggKey;
        _govKey = govKey;
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
     * @param contractMsgHash   The hash of the thing being signed but generated by the contract
     *                  to check it against the hash in sigData (bytes32) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData)
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and 
     *                  sig over that hash (uint) from the key input
     * @return          Bool used by caller to be absolutely sure that the function hasn't reverted
     */
    function isValidSig(
        bytes32 contractMsgHash,
        SigData memory sigData,
        Key memory key
    ) public override returns (bool) {
        require(sigData.msgHash == uint(contractMsgHash), "KeyManager: invalid msgHash");
        require(
            verifySignature(
                sigData.msgHash,
                sigData.sig,
                key.pubKeyX,
                key.pubKeyYParity,
                key.nonceTimesGAddr
            ),
            "KeyManager: Sig invalid"
        );
        
        _lastValidateTime = block.timestamp;
        return true;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current aggregate key
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint)
     * @param newKey    The new aggregate key to be set. The x component of the pubkey (uint),
     *                  the parity of the 7 component (uint8), and the nonce times G (address)
     */
    function setAggKeyWithAggKey(
        SigData memory sigData,
        Key memory newKey
    ) external override nzKey(newKey) 
    // validate(
    //     keccak256(abi.encodeWithSelector(
    //         this.setAggKeyWithAggKey.selector,
    //         SigData(0, 0),
    //         newKey
    //     )),
    //     sigData,
    //     _aggKey
    // ) 
    {
        require(
            isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.setAggKeyWithAggKey.selector,
                        SigData(0, 0),
                        newKey
                    )
                ),
                sigData,
                _aggKey
            )
        );

        emit KeyChange(true, _aggKey, newKey);
        _aggKey = newKey;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current governance key
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current governance key (uint)
     * @param newKey    The new aggregate key to be set. The x component of the pubkey (uint),
     *                  the parity of the 7 component (uint8), and the nonce times G (address)
     */
    function setAggKeyWithGovKey(
        SigData memory sigData,
        Key memory newKey
    ) external override nzKey(newKey) {
        require(
            isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.setAggKeyWithGovKey.selector,
                        SigData(0, 0),
                        newKey
                    )
                ),
                sigData,
                _govKey
            )
        );

        emit KeyChange(false, _aggKey, newKey);
        _aggKey = newKey;
    }

    /**
     * @notice  Set a new governance key. Requires a signature from the current governance key
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current governance key (uint)
     * @param newKey    The new governance key to be set. The x component of the pubkey (uint),
     *                  the parity of the 7 component (uint8), and the nonce times G (address)
     */
    function setGovKeyWithGovKey(
        SigData memory sigData,
        Key memory newKey
    ) external override nzKey(newKey) {
        require(
            isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.setGovKeyWithGovKey.selector,
                        SigData(0, 0),
                        newKey
                    )
                ),
                sigData,
                _govKey
            )
        );

        emit KeyChange(false, _govKey, newKey);
        _govKey = newKey;
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
        return (_aggKey);
    }

    /**
     * @notice  Get the current governance key
     * @return  The Key struct for the governance key
     */
    function getGovernanceKey() external override view returns (Key memory) {
        return (_govKey);
    }

    /**
     * @notice  Get the last time that a function was called which
                required a signature from _aggregateKeyData or _governanceKeyData
     * @return  The last time isValidSig was called, in unix time (uint)
     */
    function getLastValidateTime() external override view returns (uint) {
        return _lastValidateTime;
    }



    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    For some reason the sigData in this modifier is empty when
    ///         passed to this modifier. I've tested the exact same code
    ///         with the same compiler version (0.7) in Remix and it works,
    ///         so it's likely a bug in Brownie. It works in v0.8 in Brownie,
    ///         but there's currently no v0.8 for OpenZeppelin contracts so
    ///         we're stuck with it for now until their v0.8 release
    // modifier validate(
    //     bytes32 contractMsgHash,
    //     SigData calldata sigData,
    //     Key memory key
    // ) {
    //     require(isValidSig(contractMsgHash, sigData, key));
    //     _;
    // }
}
