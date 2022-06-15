pragma solidity ^0.8.0;

import "../interfaces/IShared.sol";
import "../interfaces/IVault.sol";

contract VaultEchidna is IShared {
    IVault public v;

    // Expose Vault functions to Echidna

    function allBatch(
        SigData calldata sigData,
        bytes32[] calldata fetchSwapIDs,
        IERC20[] calldata fetchTokens,
        IERC20[] calldata tranTokens,
        address payable[] calldata tranRecipients,
        uint256[] calldata tranAmounts
    ) external {
        v.allBatch(sigData, fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts);
    }

    function transfer(
        SigData calldata sigData,
        IERC20 token,
        address payable recipient,
        uint256 amount
    ) external {
        v.transfer(sigData, token, recipient, amount);
    }

    function transferBatch(
        SigData calldata sigData,
        IERC20[] calldata tokens,
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        v.transferBatch(sigData, tokens, recipients, amounts);
    }

    function fetchDepositEth(SigData calldata sigData, bytes32 swapID) external {
        v.fetchDepositEth(sigData, swapID);
    }

    function fetchDepositEthBatch(SigData calldata sigData, bytes32[] calldata swapIDs) external {
        v.fetchDepositEthBatch(sigData, swapIDs);
    }

    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        IERC20 token
    ) external {
        v.fetchDepositToken(sigData, swapID, token);
    }

    function fetchDepositTokenBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        IERC20[] calldata tokens
    ) external {
        v.fetchDepositTokenBatch(sigData, swapIDs, tokens);
    }

    function swapETH(string calldata egressParams, bytes32 egressReceiver) external {
        v.swapETH(egressParams, egressReceiver);
    }

    function swapToken(
        string calldata egressParams,
        bytes32 egressReceiver,
        address ingressToken,
        uint256 amount
    ) external {
        v.swapToken(egressParams, egressReceiver, ingressToken, amount);
    }

    function govWithdraw(IERC20[] calldata tokens) external {
        v.govWithdraw(tokens);
    }

    function enableSwaps() external {
        v.enableSwaps();
    }

    function disableSwaps() external {
        v.disableSwaps();
    }

    // Expose AggKeyNonceConsumer functions to Echidna

    function updateKeyManagerVault(SigData calldata sigData, IKeyManager keyManager) external {
        v.updateKeyManager(sigData, keyManager);
    }

    // Expose GovernanceCommunityGuarded functions to Echidna
    function enableCommunityGuardVault() external {
        v.enableCommunityGuard();
    }

    function disableCommunityGuardVault() external {
        v.disableCommunityGuard();
    }

    function suspendVault() external {
        v.suspend();
    }

    function resumeVault() external {
        v.resume();
    }
}
