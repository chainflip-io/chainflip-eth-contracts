// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
 * @title    Balance Checker contract
 * @notice   Checks the Native token balances of multiple addresses. This can be used to check
 *           the balances of multiple addresses in a single call instead of issuing a separate
 *           call for each address, which is very innefficient.
 * @dev      This contract only contains view functions that doesn't spend gas. However, some RPC
 *           providers put a cap on the amount of gas that the transaction *would* consume to
 *           prevent spamming. As a rough refernece, a try using a free INFURA endpoint succesfully
 *           executes around 75k addresses but fails when requesting 100k. It's advised to split
 *           up such big lists.
 */
contract BalanceChecker {
    struct BalanceAndDeployedStatus {
        uint256 balance;
        bool deployed;
    }

    /**
     * @notice  Returns an array of native token balances for an array of addresses.
     * @param addresses  Array of addresses to check.
     */
    function getNativeBalances(address[] calldata addresses) external view returns (uint[] memory) {
        uint256 length = addresses.length;

        uint[] memory balances = new uint[](length);

        for (uint i = 0; i < length; ) {
            balances[i] = addresses[i].balance;
            unchecked {
                ++i;
            }
        }
        return balances;
    }

    /**
     * @notice  Returns an array of booleans signaling whether there is bytecode deployed for an array of addresses.
     * @param addresses  Array of addresses to check.
     */
    function getDeployedStatus(address[] calldata addresses) external view returns (bool[] memory) {
        uint256 length = addresses.length;

        bool[] memory deployedStatus = new bool[](length);

        for (uint i = 0; i < length; ) {
            deployedStatus[i] = addresses[i].code.length > 0;
            unchecked {
                ++i;
            }
        }
        return deployedStatus;
    }

    /**
     * @notice  Returns an array of structs with both the native token balance and whether the addresses have bytecode
     *          deployed for for an array of addresses.
     * @param addresses  Array of addresses to check.
     */
    function getNativeBalancesAndDeployedStatus(
        address[] calldata addresses
    ) external view returns (BalanceAndDeployedStatus[] memory) {
        uint256 length = addresses.length;

        BalanceAndDeployedStatus[] memory balanceAndDeployedStatus = new BalanceAndDeployedStatus[](length * 2);

        for (uint i = 0; i < length; ) {
            balanceAndDeployedStatus[i] = BalanceAndDeployedStatus(addresses[i].balance, addresses[i].code.length > 0);
            unchecked {
                ++i;
            }
        }
        return balanceAndDeployedStatus;
    }
}
