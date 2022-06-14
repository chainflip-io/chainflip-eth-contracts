pragma solidity ^0.8.0;

import "../interfaces/IShared.sol";
import "../interfaces/IStakeManager.sol";

contract StakeManagerEchidna is IShared {
    IStakeManager public sm;

    // Expose StakeManager functions to Echidna

    function setFlip(FLIP flip) external {
        sm.setFlip(flip);
    }

    function stake(
        bytes32 nodeID,
        uint256 amount,
        address returnAddr
    ) external {
        // TODO: Add approve tokens function?
        sm.stake(nodeID, amount, returnAddr);
    }

    function registerClaim(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address staker,
        uint48 expiryTime
    ) external {
        sm.registerClaim(sigData, nodeID, amount, staker, expiryTime);
    }

    function executeClaim(bytes32 nodeID) external {
        sm.executeClaim(nodeID);
    }

    function setMinStake(uint256 newMinStake) external {
        sm.setMinStake(newMinStake);
    }

    function govWithdraw() external {
        sm.govWithdraw();
    }

    function govWithdrawEth() external {
        sm.govWithdrawEth();
    }
}
