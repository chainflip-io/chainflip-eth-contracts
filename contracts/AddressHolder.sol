// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./interfaces/IAddressHolder.sol";
import "./abstract/Shared.sol";

/**
 * @title Address Holder reference
 * @dev A contract that holds a reference to an address. This reference address can only be updated
 *      by the governor. This is used for the TokenVesting contracts so the governor doesn't have
 *      update multiple references in case of the StateChainGateway contract being upgraded.
 */
contract AddressHolder is IAddressHolder, Shared {
    address private governor;

    address private referenceAddress;

    constructor(address _governor, address _referenceAddress) nzAddr(_governor) nzAddr(_referenceAddress) {
        governor = _governor;
        referenceAddress = _referenceAddress;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Update the reference address
    function updateReferenceAddress(
        address _referenceAddress
    ) external override onlyGovernor nzAddr(_referenceAddress) {
        address oldReferenceAddress = referenceAddress;
        referenceAddress = _referenceAddress;
        emit ReferenceAddressUpdated(oldReferenceAddress, _referenceAddress);
    }

    /// @dev    Allow the governor to transfer governance to a new address in case of need
    function transferGovernor(address _governor) external override onlyGovernor nzAddr(_governor) {
        address oldGovernor = governor;
        governor = _governor;
        emit GovernorTransferred(oldGovernor, _governor);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Getter function for the reference address
    function getReferenceAddress() external view override returns (address) {
        return referenceAddress;
    }

    /// @dev    Getter function for the governor address
    function getGovernor() external view override returns (address) {
        return governor;
    }

    /// @notice Ensure that the caller is the governor address.
    modifier onlyGovernor() {
        require(msg.sender == governor, "AddrHolder: not the governor");
        _;
    }
}
