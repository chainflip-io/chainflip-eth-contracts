pragma solidity ^0.8.0;

import "./interfaces/IKeyManager.sol";
import "./interfaces/IAccessValidator.sol";
import "./abstract/Shared.sol";

/**
 * @title    AccessValidator contract
 * @notice   Manages the reference to the KeyManager contract. The address
 *           is set in the constructor and can only be updated with a valid
 *           signature validated by the current KeyManager contract. This shall
 *           be done if the KeyManager contract is updated.
 * @author   albert-llimos (Albert Llimos)
 */
contract AccessValidator is Shared, IAccessValidator {
    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;

    constructor(IKeyManager keyManager) nzAddr(address(keyManager)) {
        _keyManager = keyManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Update KeyManager reference. Used if KeyManager contract is updated
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param keyManager New KeyManager's address
     */
    function updateKeyManager(SigData calldata sigData, IKeyManager keyManager)
        external
        override
        nzAddr(address(keyManager))
        updatedValidSig(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.updateKeyManager.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    keyManager
                )
            )
        )
    {
        _keyManager = keyManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external view override returns (IKeyManager) {
        return _getKeyManager();
    }

    /**
     * @notice  Internal getter so child contracts can access the _keyManager reference
     *          but cannot modify it as it is kept private.
     * @return  The KeyManager (IKeyManager)
     */
    function _getKeyManager() internal view returns (IKeyManager) {
        return _keyManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                         Modifiers                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Calls isUpdatedValidSig in _keyManager
    modifier updatedValidSig(SigData calldata sigData, bytes32 contractMsgHash) {
        require(_keyManager.isUpdatedValidSig(sigData, contractMsgHash));
        _;
    }
}
