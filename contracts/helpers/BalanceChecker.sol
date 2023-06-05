// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
 * @title    Balance Checker contract
 * @notice   Checks the Native token balances of multiple addresses. This can be used to check
 *           the balances of multiple addresses in a single call instead of issuing a separate
 *           call for each address, which is very innefficient.
 */
contract BalanceChecker {
    /**
     * @notice  Returns an array of native token balances for an array of addresses.
     * @dev     Even though this function is a view function and should not spend gas when called
     *          directly, there can be some limitation on the amount of computation that it can do.
     *          Some node providers put a cap on the amount of computation/gas that can be used.
     * @param addresses  Array of addresses to get the balance of.
     */
    function balancesNative(address[] calldata addresses) external view returns (uint[] memory) {
        uint256 length = addresses.length;

        uint[] memory addrBalances = new uint[](length);

        for (uint i = 0; i < length; ) {
            addrBalances[i] = addresses[i].balance;
            unchecked {
                ++i;
            }
        }
        return addrBalances;
    }
}
