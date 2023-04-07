pragma solidity ^0.8.0;

import "../KeyManager.sol";
import "../StakeManager.sol";
import "../FLIP.sol";
import "../abstract/Shared.sol";

/**
 * @title    Deployer of a new StakeManager contract
 * @notice   Contract used to upgrade the StakeManager contract. It assumes that
 *           the FLIP and the KeyManager contracts have already been deployed.
 *           The whitelisting and funds will need to be upgraded by the State Chain.
 */
contract DeployerStakeManager is Shared {
    KeyManager public immutable keyManager;
    StakeManager public immutable stakeManager;
    FLIP public immutable flip;

    constructor(
        uint256 minStake,
        KeyManager _keyManager,
        FLIP _flip
    ) nzAddr(address(_keyManager)) nzAddr(address(_flip)) {
        StakeManager _stakeManager = new StakeManager(_keyManager, minStake);

        // Set the FLIP address in the StakeManager contract
        _stakeManager.setFlip(FLIP(address(_flip)));

        // Storing all addresses for traceability.
        keyManager = _keyManager;
        stakeManager = _stakeManager;
        flip = _flip;
    }
}
