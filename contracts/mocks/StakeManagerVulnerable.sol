pragma solidity ^0.8.0;

import "../StakeManager.sol";
import "../FLIP.sol";

/**
 * @title    StakeManagerVulnerable
 * @dev      This is purely for testing `noFish` which requires adding
 *           adding a fcn to send FLIP outside the contract without
 *           calling `claim`
 * @author   Quantaf1re (James Key)
 */
contract StakeManagerVulnerable is StakeManager {
    constructor(IKeyManager keyManager, uint256 minStake) StakeManager(keyManager, minStake) {}

    /**
     * @notice  Transfers FLIP out the contract
     * @param receiver  The address to send the FLIP to
     * @param amount    The amount of FLIP to send
     */
    function testSendFLIP(address receiver, uint256 amount) external {
        require(this.getFLIP().transfer(receiver, amount));
    }
}
