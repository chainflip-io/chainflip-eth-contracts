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
    // Disable because tokens are usually in caps
    // solhint-disable-next-line var-name-mixedcase
    FLIP private _FLIP;

    constructor(
        IKeyManager keyManager,
        uint256 minStake,
        uint256 flipTotalSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake
    ) StakeManager(keyManager, minStake, flipTotalSupply, numGenesisValidators, genesisStake) {}

    //
    /**
     * @notice  Can't set _FLIP in the constructor because it's made in the constructor
     *          of StakeManager and getFLIP is external
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
    function testSendFLIP(address receiver, uint256 amount) external {
        // Disable because it would revert inside the transfer providing a reason-string
        // solhint-disable-next-line reason-string
        require(_FLIP.transfer(receiver, amount));
    }
}
