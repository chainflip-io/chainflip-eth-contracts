// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IAddressChecker {
    struct AddressState {
        uint256 balance;
        bool hasContract;
    }

    function nativeBalances(address[] calldata addresses) external view returns (uint[] memory);

    function contractsDeployed(address[] calldata addresses) external view returns (bool[] memory);

    function addressStates(address[] calldata addresses) external view returns (AddressState[] memory);
}
