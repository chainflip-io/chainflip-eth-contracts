pragma solidity ^0.8.0;

import "../../interfaces/IShared.sol";
import "../../interfaces/IVault.sol";

contract VaultEchidna is IShared {
    IVault public v;

    // Expose Vault functions to Echidna - making them virtual to override them in tests when needed

    function allBatch(
        SigData calldata sigData,
        bytes32[] calldata fetchSwapIDs,
        IERC20[] calldata fetchTokens,
        IERC20[] calldata tranTokens,
        address payable[] calldata tranRecipients,
        uint256[] calldata tranAmounts
    ) external virtual {
        v.allBatch(sigData, fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts);
    }

    function transfer(
        SigData calldata sigData,
        IERC20 token,
        address payable recipient,
        uint256 amount
    ) external virtual {
        v.transfer(sigData, token, recipient, amount);
    }

    function transferBatch(
        SigData calldata sigData,
        IERC20[] calldata tokens,
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) external virtual {
        v.transferBatch(sigData, tokens, recipients, amounts);
    }

    function fetchDepositEth(SigData calldata sigData, bytes32 swapID) external virtual {
        v.fetchDepositEth(sigData, swapID);
    }

    function fetchDepositEthBatch(SigData calldata sigData, bytes32[] calldata swapIDs) external virtual {
        v.fetchDepositEthBatch(sigData, swapIDs);
    }

    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        IERC20 token
    ) external virtual {
        v.fetchDepositToken(sigData, swapID, token);
    }

    function fetchDepositTokenBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        IERC20[] calldata tokens
    ) external virtual {
        v.fetchDepositTokenBatch(sigData, swapIDs, tokens);
    }

    function swapETH(string calldata egressParams, bytes32 egressReceiver) external virtual {
        v.swapETH(egressParams, egressReceiver);
    }

    function swapToken(
        string calldata egressParams,
        bytes32 egressReceiver,
        address ingressToken,
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
