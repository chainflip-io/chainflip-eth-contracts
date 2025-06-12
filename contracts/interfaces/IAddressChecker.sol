// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IAddressChecker {
    struct AddressState {
        uint256 balance;
        bool hasContract;
    }

    struct PriceFeedData {
        uint80 roundId;
        int256 answer;
        uint256 startedAt;
        uint256 updatedAt;
        uint80 answeredInRound;
        uint8 decimals;
        string description;
    }

    function nativeBalances(address[] calldata addresses) external view returns (uint[] memory);

    function contractsDeployed(address[] calldata addresses) external view returns (bool[] memory);

    function addressStates(address[] calldata addresses) external view returns (AddressState[] memory);

    function queryPriceFeeds(
        address[] calldata addresses
    ) external view returns (uint256 blockNumber, uint256 blockTimestamp, PriceFeedData[] memory);
}
