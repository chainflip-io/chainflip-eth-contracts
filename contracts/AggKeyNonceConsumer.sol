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
        // Updating this to an address that is not a IKeyManager would basically brick all the
        // calls that require a call to the KeyManager. In the case of the Vault and the
        // StateChainGateway, they would completely brick the contract. We would not be able
        // to validate any signature, nor get any of the addresses govKey, aggKey, commKey
        // nor getLastValidateTime() so we wouldn't even be able to do any govWithdrawal nor any
        // other emergency action. The procotol would be bricked and everything would be lost.
        // Therefore, we aim to check that all the interfaces needed are implemented.
        // This is just to avoid that updating to a wrong address becomes a catastrophic mistake.
        // If an attacker controls the aggKey we are screwed anyway.
        // Just as a note, we don't care about gas at all in this function.

        // This contract will check that consumeKeyNonce is implemented while the child contract
        // inheriting this should add their own checks in _doSafeKeyManagerUpdateCheck(). That is
        // any function call that performs to the IKeyManager.

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

        // Revert without a reason string to match the try-catch behaviour
        require(address(keyManager).code.length > 0);
        // Making a low level call with zero values expecting a revert with some return data. These
        // arbitrary values should never pass signature verification so it should always revert.
        (bool success, bytes memory returndata) = address(keyManager).call(
            abi.encodeWithSelector(IKeyManager.consumeKeyNonce.selector, SigData(0, 0, address(0)), bytes32(0))
        );

        // The call should fail (revert) with a string. Otherwise it will mean that it has not found the function.
        // That is assuming that all the reverts in the keyManager are done with a string.
        // In case of a EOA, it will succeed, so we don'e even need to check that.
        // This does not check that the return value type is correct (no return ) but we don't need that.
        // We allow it to succeed
        if (!success) {
            require(returndata.length > 0, "NonceCons: not consumeKeyNonce implementer");
        }
        // In the success case we could check that returndata.length == 0 to enforce the return type (nothing)
        // which we can't do in try-catch. But it doesn't seem necessary

        ///////////////////////////////////////////////////////////////////////////////////

        // OPTION 3:

        // This should not succeed. Only issue with this approach is that if consumeKeyNonce returns a value
        // instead of nothing it will not catch it, as our interface definition doesn't have any type.
        // This shouldn't be a problem but I guess it could be a problem if we want to upgrade to a keyManager
        // that instead of reverting it returns a bool. However, in that case this will pass and we should then
        // be upgrading the AggKeyNonceConsumer properly to address that. So it is most likely fine.
        // Another difference with the lowLevelCall is that we are not enforcing it to fail here, as
        // it's not really necessary. In the LowLeveCall we enforce it as it succeeds on EOAs, but we could
        // technically check it separately.

        // This will fail with no message if the keymanager is not a contract (it's not catched), which is fine.
        try keyManager.consumeKeyNonce(SigData(0, 0, address(0)), bytes32(0)) {
            // No need to enforce that it fails.
        } catch (bytes memory reason) {
            // We allow/expect either a reverts string reason or a custom Error.
            if (reason.length == 0) {
                revert("NonceCons: not consumeKeyNonce implementer");
            }
        }

        // NOTE: The only limitation of these two approaches is that the KeyManager shall never revert with no data
        // (no string on require or no custom Error) as this will be confused with not having the function
        // implemented. I don't think this is really a problem as we will be testing this upon upgrade and it
        // will just fail to upgrade in that case, not a big issue.
        // The other option of implementing `supportsConsumeKeyNonce` doesn't ensure that consumeKeyNonce is
        // actually implemented either, it's more like a note for the developer. So it's a weaker check.

        ///////////////////////////////////////////////////////////////////////////////////

        // for all options continue here:

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
