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
        sm.getFLIP().approve(address(sm), amount);
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

    // Expose AggKeyNonceConsumer functions to Echidna

    function updateKeyManagerStakeManager(SigData calldata sigData, IKeyManager keyManager) external {
        sm.updateKeyManager(sigData, keyManager);
    }

    // Expose GovernanceCommunityGuarded functions to Echidna

    function enableCommunityGuardStakeManager() external {
        sm.enableCommunityGuard();
    }

    function disableCommunityGuardStakeManager() external {
        sm.disableCommunityGuard();
    }

    function suspendStakeManager() external {
        sm.suspend();
    }

    function resumeStakeManager() external {
        sm.resume();
    }
}
