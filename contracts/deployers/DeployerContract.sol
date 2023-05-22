// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../Vault.sol";
import "../KeyManager.sol";
import "../StateChainGateway.sol";
import "../FLIP.sol";
import "../interfaces/IShared.sol";

/**
 * @title    Deployer contract
 * @notice   Upon deployment of this contract, all the necessary contracts will be
 *           deployed in a single transaction. This give atomocity to the deployment
 *           flow by deploying all the contracts and setting them up appropriately.
 */
contract DeployerContract is IShared {
    Vault public immutable vault;
    KeyManager public immutable keyManager;
    StateChainGateway public immutable stateChainGateway;
    FLIP public immutable flip;

    // The underlying contracts will check for non-zero inputs.
    constructor(
        Key memory aggKey,
        address govKey,
        address commKey,
        uint256 minFunding,
        uint256 initSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake
    ) {
        KeyManager _keyManager = new KeyManager(aggKey, govKey, commKey);
        Vault _vault = new Vault(_keyManager);
        StateChainGateway _stateChainGateway = new StateChainGateway(_keyManager, minFunding);
        FLIP _flip = new FLIP(
            initSupply,
            numGenesisValidators,
            genesisStake,
            address(_stateChainGateway),
            govKey,
            address(_stateChainGateway)
        );
        // Set the FLIP address in the StateChainGateway contract
        _stateChainGateway.setFlip(_flip);

        // Storing all addresses for traceability.
        vault = _vault;
        keyManager = _keyManager;
        stateChainGateway = _stateChainGateway;
        flip = _flip;
    }
}
