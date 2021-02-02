pragma solidity ^0.7.0;
pragma abicoder v2;


import "../StakeManager.sol";
import "../FLIP.sol";


/**
* @dev  This is purely for testing `noFish` which requires adding
*       adding a fcn to send FLIP outside the contract without
*       calling `claim`
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

    // Can't set _FLIP in the constructor because it's made in the constructor
    // of StakeManager and getFLIPAddress is external
    function testSetFLIP(FLIP flip) external {
        _FLIP = flip;
    }

    function testSendFLIP(address receiver, uint amount) external {
        _FLIP.transfer(receiver, amount);
    }

}