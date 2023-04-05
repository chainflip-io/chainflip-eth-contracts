pragma solidity ^0.8.0;

import "../Vault.sol";
import "../KeyManager.sol";
import "../StakeManager.sol";
import "../FLIP.sol";
import "../abstract/Shared.sol";

/**
 * @title    Deployer of upgraded contracts
 * @notice   Contract to use to upgrade the Vault and the StakeManager
 *           contracts. It assumes that the FLIP and the KeyManager contracts
 *           have already been deployed.
 *           The whitelisting and funds will need to be upgraded by the State Chain.
 */
contract DeployerUpgradedContracts is Shared {
    Vault public immutable vault;
    KeyManager public immutable keyManager;
    StakeManager public immutable stakeManager;
    FLIP public immutable flip;

    constructor(
        uint256 minStake,
        KeyManager _keyManager,
        FLIP _flip
    ) nzAddr(address(_keyManager)) nzAddr(address(_flip)) {
        Vault _vault = new Vault(_keyManager);
        StakeManager _stakeManager = new StakeManager(_keyManager, minStake);

        // Set the FLIP address in the StakeManager contract
        _stakeManager.setFlip(FLIP(address(_flip)));

        // Set values to storage
        vault = _vault;
        keyManager = _keyManager;
        stakeManager = _stakeManager;
        flip = _flip;
    }
}
