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
     */
    function updateKeyManager(
        SigData calldata sigData,
        IKeyManager keyManager
    )
        external
        override
        nzAddr(address(keyManager))
        consumesKeyNonce(sigData, keccak256(abi.encode(this.updateKeyManager.selector, keyManager)))
    {
        // OPTION 1:
        ///////////////////////////////////////////////////////////////////////////////////
        // require(
        //     keyManager.supportsConsumeKeyNonce() == IKeyManager.consumeKeyNonce.selector,
        //     "NonceCons: not consumeKeyNonce implementer"
        // );

        // // Then add this to the KeyManager:
        // function supportsConsumeKeyNonce() external pure override returns (bytes4) {
        //     return this.consumeKeyNonce.selector;
        // }
        ///////////////////////////////////////////////////////////////////////////////////

        // OPTION 2:

        // Check that it's a contract - revert without a reason string to match the try-catch behaviour of option 2
        require(address(keyManager).code.length > 0);

        // Making a low level call with arbitrary values.
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, bytes memory returndata) = address(keyManager).call(
            abi.encodeWithSelector(IKeyManager.consumeKeyNonce.selector, SigData(0, 0, address(0)), bytes32(0))
        );

        // No need to enforce that it fails (tbd).
        // If it fails (as it should), we check that there is a revert reason (string/error). Otherwise we
        // assume the function doesn't exist.
        if (!success) {
            require(returndata.length > 0, "NonceCons: not consumeKeyNonce implementer");
        }

        ///////////////////////////////////////////////////////////////////////////////////

        // OPTION 3:

        // This will fail with no message if the keymanager is not a contract - it's not catched, which is fine.
        try keyManager.consumeKeyNonce(SigData(0, 0, address(0)), bytes32(0)) {
            // No need to enforce that it fails (tbd)
        } catch (bytes memory reason) {
            // We allow/expect either a reverts string reason or a custom Error.
            require(reason.length > 0, "NonceCons: not consumeKeyNonce implementer");
        }

        ///////////////////////////////////////////////////////////////////////////////////

        // for any options continue here:

        // For view functions we just call them and they will revert if they don't exist or if the return type
        // is not the expected one.
        _doSafeKeyManagerUpdateCheck(keyManager);

        _keyManager = keyManager;
        emit UpdatedKeyManager(address(keyManager));
    }

    /// @dev   This will be called when upgrading to a new KeyManager. This should check every
    //         function that this child's contract needs to call from the new keyManager to
    //         check that it's implemented. This is to ensure that the new KeyManager is
    //         compatible with this contract and prevents bricking it.
    function _doSafeKeyManagerUpdateCheck(IKeyManager keyManager) internal view virtual;

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
