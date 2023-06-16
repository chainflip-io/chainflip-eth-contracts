// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../../interfaces/IShared.sol";
import "../../interfaces/IVault.sol";

contract VaultEchidna is IShared {
    IVault public v;

    // Expose Vault functions to Echidna - making them virtual to override them in tests when needed

    function allBatch(
        SigData calldata sigData,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    ) external virtual {
        v.allBatch(sigData, fetchParamsArray, transferParamsArray);
    }

    function transfer(SigData calldata sigData, TransferParams calldata transferParams) external virtual {
        v.transfer(sigData, transferParams);
    }

    function transferBatch(SigData calldata sigData, TransferParams[] calldata transferParamsArray) external virtual {
        v.transferBatch(sigData, transferParamsArray);
    }

    function deployAndFetchBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray
    ) external virtual {
        v.deployAndFetchBatch(sigData, deployFetchParamsArray);
    }

    function fetchBatch(SigData calldata sigData, FetchParams[] calldata fetchParamsArray) external virtual {
        v.fetchBatch(sigData, fetchParamsArray);
    }

    function xSwapNative(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata cfParameters
    ) external payable virtual {
        v.xSwapNative{value: msg.value}(dstChain, dstAddress, dstToken, cfParameters);
    }

    function xSwapToken(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external virtual {
        v.xSwapToken(dstChain, dstAddress, dstToken, srcToken, amount, cfParameters);
    }

    function xCallNative(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 dstNativeGas,
        bytes calldata cfParameters
    ) external payable virtual {
        v.xCallNative{value: msg.value}(dstChain, dstAddress, dstToken, message, dstNativeGas, cfParameters);
    }

    function xCallToken(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 dstNativeGas,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external virtual {
        v.xCallToken(dstChain, dstAddress, dstToken, message, dstNativeGas, srcToken, amount, cfParameters);
    }

    function executexSwapAndCall(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external virtual {
        v.executexSwapAndCall(sigData, transferParams, srcChain, srcAddress, message);
    }

    function executexCall(
        SigData calldata sigData,
        address recipient,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external virtual {
        v.executexCall(sigData, recipient, srcChain, srcAddress, message);
    }

    function govWithdraw(address[] calldata tokens) external virtual {
        v.govWithdraw(tokens);
    }

    // Expose AggKeyNonceConsumer functions to Echidna

    function updateKeyManagerVault(SigData calldata sigData, IKeyManager keyManager, bool omitChecks) external virtual {
        v.updateKeyManager(sigData, keyManager, omitChecks);
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
