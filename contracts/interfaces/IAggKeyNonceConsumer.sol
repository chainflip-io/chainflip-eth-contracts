// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./IShared.sol";
import "./IKeyManager.sol";

/**
 * @title    AggKeyNonceConsumer interface
 */

interface IAggKeyNonceConsumer is IShared {
    event UpdatedKeyManager(address keyManager);

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
     * @param omitChecks Allow the omission of the extra checks in a special case
     */
    function updateKeyManager(SigData calldata sigData, IKeyManager keyManager, bool omitChecks) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external view returns (IKeyManager);
}
