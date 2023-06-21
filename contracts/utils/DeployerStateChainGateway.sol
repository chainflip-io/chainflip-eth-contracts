// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../KeyManager.sol";
import "../StateChainGateway.sol";
import "../FLIP.sol";
import "../abstract/Shared.sol";

/**
 * @title    Deployer of a new StateChainGateway contract
 * @notice   Contract used to upgrade the StateChainGateway contract. It assumes that
 *           the FLIP and the KeyManager contracts have already been deployed.
 */
contract DeployerStateChainGateway is Shared {
    KeyManager public immutable keyManager;
    StateChainGateway public immutable stateChainGateway;
    FLIP public immutable flip;

    constructor(
        uint256 minFunding,
        uint48 redemptionDelay,
        KeyManager _keyManager,
        FLIP _flip
    ) nzAddr(address(_keyManager)) nzAddr(address(_flip)) {
        StateChainGateway _stateChainGateway = new StateChainGateway(_keyManager, minFunding, redemptionDelay);

        // Set the FLIP address in the StateChainGateway contract
        _stateChainGateway.setFlip(FLIP(address(_flip)));

        // Storing all addresses for traceability.
        keyManager = _keyManager;
        stateChainGateway = _stateChainGateway;
        flip = _flip;
    }
}
