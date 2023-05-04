pragma solidity ^0.8.0;

import "./interfaces/IKeyManager.sol";
import "./interfaces/IAggKeyNonceConsumer.sol";
import "./abstract/Shared.sol";

/**
 * @title    AggKeyNonceConsumer contract
 * @notice   Manages the reference to the KeyManager contract. The address
 *           is set in the constructor and can only be updated with a valid
 *           signature validated by the current KeyManager contract. This shall
 *           be done if the KeyManager contract is updated.
 */
abstract contract AggKeyNonceConsumer is Shared, IAggKeyNonceConsumer {
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
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param keyManager New KeyManager's address
     * @param omitValueChecks We want to allow for an option to skip the extra checks
     * in some special cases - mainly to avoid potentially not being able to upgrade.
     */
    function updateKeyManager(
        SigData calldata sigData,
        IKeyManager keyManager,
        bool omitValueChecks
    )
        external
        override
        nzAddr(address(keyManager))
        consumesKeyNonce(sigData, keccak256(abi.encode(this.updateKeyManager.selector, keyManager, omitValueChecks)))
    {
        // Check that the new KeyManager is a contract
        require(address(keyManager).code.length > 0);

        // Allow the child to check that the new KeyManager is compatible
        _doSafeKeyManagerUpdateCheck(keyManager, omitValueChecks);

        _keyManager = keyManager;
        emit UpdatedKeyManager(address(keyManager));
    }

    /// @dev   This will be called when upgrading to a new KeyManager. This should check every
    //         function that this child's contract needs to call from the new keyManager to
    //         check that it's implemented. This is to ensure that the new KeyManager is
    //         compatible with this contract and prevents it from bricking.
    function _doSafeKeyManagerUpdateCheck(IKeyManager keyManager, bool omitValueChecks) internal view virtual;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() public view override returns (IKeyManager) {
        return _keyManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                         Modifiers                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Calls consumeKeyNonce in _keyManager
    modifier consumesKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) {
        getKeyManager().consumeKeyNonce(sigData, contractMsgHash);
        _;
    }
}
