// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../../interfaces/IShared.sol";
import "../../interfaces/IStateChainGateway.sol";

contract StateChainGatewayEchidna is IShared {
    IStateChainGateway public sm;

    // Expose StateChainGateway functions to Echidna - making them virtual to override them in tests when needed

    function setFlip(IFLIP flip) external virtual {
        sm.setFlip(flip);
    }

    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external virtual {
        sm.getFLIP().approve(address(sm), amount);
        sm.fundStateChainAccount(nodeID, amount);
    }

    function registerRedemption(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address redeemAddress,
        uint48 expiryTime,
        address executor
    ) external virtual {
        sm.registerRedemption(sigData, nodeID, amount, redeemAddress, expiryTime, executor);
    }

    function executeRedemption(bytes32 nodeID) external virtual {
        sm.executeRedemption(nodeID);
    }

    function setMinFunding(uint256 newMinFunding) external virtual {
        sm.setMinFunding(newMinFunding);
    }

    function govWithdraw() external virtual {
        sm.govWithdraw();
    }

    // Expose AggKeyNonceConsumer functions to Echidna

    function updateKeyManagerStateChainGateway(
        SigData calldata sigData,
        IKeyManager keyManager,
        bool omitChecks
    ) external virtual {
        sm.updateKeyManager(sigData, keyManager, omitChecks);
    }

    // Expose GovernanceCommunityGuarded functions to Echidna

    function enableCommunityGuardStateChainGateway() external virtual {
        sm.enableCommunityGuard();
    }

    function disableCommunityGuardStateChainGateway() external virtual {
        sm.disableCommunityGuard();
    }

    function suspendStateChainGateway() external virtual {
        sm.suspend();
    }

    function resumeStateChainGateway() external virtual {
        sm.resume();
    }
}
