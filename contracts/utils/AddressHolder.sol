// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../interfaces/IAddressHolder.sol";
import "../abstract/Shared.sol";

/**
 * @title Address' Holder reference
 * @dev A contract that holds references to addresses. This reference address can only be updated
 *      by the governor. This can be used when multiple contracts hold references to the same
 *      addresses that may need to be updated. In that case, it is easier to have a single contract
 *      that holds all the addresses.
 */
contract AddressHolder is IAddressHolder, Shared {
    address private governor;

    address private stateChainGateway;

    address private stFLIP;
    address private stMinter;
    address private stBurner;

    // @dev Allow stAddresses to be zero as they might not be known at the time of deployment
    constructor(
        address _governor,
        address _stateChainGateway,
        address _stFLIP,
        address _stMinter,
        address _stBurner
    ) nzAddr(_governor) nzAddr(_stateChainGateway) {
        governor = _governor;
        stateChainGateway = _stateChainGateway;
        stFLIP = _stFLIP;
        stMinter = _stMinter;
        stBurner = _stBurner;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Update the reference address
    function updateStateChainGateway(
        address _stateChainGateway
    ) external override onlyGovernor nzAddr(_stateChainGateway) {
        emit StateChainGatewayUpdated(stateChainGateway, _stateChainGateway);
        stateChainGateway = _stateChainGateway;
    }

    /// @dev    Update the reference addresses
    function updateStakingAddresses(
        address _stFLIP,
        address _stMinter,
        address _stBurner
    ) external override onlyGovernor nzAddr(_stFLIP) nzAddr(_stMinter) nzAddr(_stBurner) {
        emit StakingAddressesUpdated(stFLIP, stMinter, stBurner, _stFLIP, _stMinter, _stBurner);
        stFLIP = _stFLIP;
        stMinter = _stMinter;
        stBurner = _stBurner;
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
    function getStateChainGateway() external view override returns (address) {
        return stateChainGateway;
    }

    function getStakingAddress() external view override returns (address) {
        return stMinter;
    }

    function getUnstakingAddresses() external view override returns (address, address) {
        return (stFLIP, stBurner);
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
