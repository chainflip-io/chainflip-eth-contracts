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
        // This is just to avoid a catastrophic mistake. If an attacker controls the aggKey
        // we are screwed anyway.

        // This contract will "check" the consumeKeyNonce while the child contract inheriting
        // this should add their own checks in _checkKeyManager().

        // We can't really call consumeKeyNonce so we follow a similar approach to the standards
        // in ERC721, ERC1155... but returning consumeKeyNonce.selector, not
        // onKeyManagerUpdated.selector as we require the specific consumeKeyNonce function.
        require(
            keyManager.onKeyManagerUpdated() == IKeyManager.consumeKeyNonce.selector,
            "NonceCons: not consumeKeyNonce implementer"
        );
        _checkKeyManager(keyManager);

        _keyManager = keyManager;
        emit UpdatedKeyManager(address(keyManager));
    }

    /// @dev   This will be called when upgrading to a new KeyManager. This should check every
    //         function that this contract needs to call from the new keyManager to ensure that
    //         it's implemented. This is to ensure that the new KeyManager is compatible with
    //         this contract.
    function _checkKeyManager(IKeyManager keyManager) internal view virtual;

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
