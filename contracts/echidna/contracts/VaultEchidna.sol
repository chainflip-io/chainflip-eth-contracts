pragma solidity ^0.8.0;

import "../../interfaces/IShared.sol";
import "../../interfaces/IVault.sol";

contract VaultEchidna is IShared {
    IVault public v;

    // Expose Vault functions to Echidna - making them virtual to override them in tests when needed

    function allBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    ) external virtual {
        v.allBatch(sigData, deployFetchParamsArray, fetchParamsArray, transferParamsArray);
    }

    function transfer(SigData calldata sigData, TransferParams calldata transferParams) external virtual {
        v.transfer(sigData, transferParams);
    }

    function transferBatch(SigData calldata sigData, TransferParams[] calldata transferParamsArray) external virtual {
        v.transferBatch(sigData, transferParamsArray);
    }

    function deployAndFetchBatch(SigData calldata sigData, DeployFetchParams[] calldata deployFetchParamsArray)
        external
        virtual
    {
        v.deployAndFetchBatch(sigData, deployFetchParamsArray);
    }

    function fetchBatch(SigData calldata sigData, FetchParams[] calldata fetchParamsArray) external virtual {
        v.fetchBatch(sigData, fetchParamsArray);
    }

    function swapNative(string calldata egressParams, bytes32 egressReceiver) external virtual {
        v.swapNative(egressParams, egressReceiver);
    }

    function swapToken(
        string calldata egressParams,
        bytes32 egressReceiver,
        IERC20 ingressToken,
        uint256 amount
    ) external virtual {
        v.swapToken(egressParams, egressReceiver, ingressToken, amount);
    }

    function govWithdraw(IERC20[] calldata tokens) external virtual {
        v.govWithdraw(tokens);
    }

    function enableSwaps() external virtual {
        v.enableSwaps();
    }

    function disableSwaps() external virtual {
        v.disableSwaps();
    }

    // Expose AggKeyNonceConsumer functions to Echidna

    function updateKeyManagerVault(SigData calldata sigData, IKeyManager keyManager) external virtual {
        v.updateKeyManager(sigData, keyManager);
    }

    // Expose GovernanceCommunityGuarded functions to Echidna
    function enableCommunityGuardVault() external virtual {
        v.enableCommunityGuard();
    }

    function disableCommunityGuardVault() external virtual {
        v.disableCommunityGuard();
    }

    function suspendVault() external virtual {
        v.suspend();
    }

    function resumeVault() external virtual {
        v.resume();
    }
}
