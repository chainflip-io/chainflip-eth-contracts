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

    /// @dev    The FLIP token
    FLIP private _FLIP;

    constructor(
        IKeyManager keyManager,
        uint emissionPerBlock,
        uint minStake,
        uint flipTotalSupply
    ) StakeManager(keyManager, emissionPerBlock, minStake, flipTotalSupply) {}

    // 
    /**
     * @notice  Can't set _FLIP in the constructor because it's made in the constructor
     *          of StakeManager and getFLIPAddress is external
     * @param flip      The address of the FLIP contract
     */
    function testSetFLIP(FLIP flip) external {
        _FLIP = flip;
    }

    /**
     * @notice  Transfers FLIP out the contract
     * @param receiver  The address to send the FLIP to
     * @param amount    The amount of FLIP to send
     */
    function testSendFLIP(address receiver, uint amount) external {
        require(_FLIP.transfer(receiver, amount));
    }
}