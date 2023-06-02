// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./interfaces/ISCGatewayReference.sol";
import "./abstract/Shared.sol";

/**
 * @title State Chain Gateway Reference
 * @dev A contract that holds a reference to the StateChainGateway contract. This is for the
 *      tokenVesting contracts so the governor doesn't have to update multiple references in case
 *      of the StateChainGateway contract being upgraded.
 */
contract SCGatewayReference is ISCGatewayReference, Shared {
    address private governor;

    IStateChainGateway private stateChainGateway;

    constructor(
        address _governor,
        IStateChainGateway _stateChainGateway
    ) nzAddr(_governor) nzAddr(address(_stateChainGateway)) {
        governor = _governor;
        stateChainGateway = _stateChainGateway;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Update the reference to the StateChainGateway contract
    function updateStateChainGateway(
        IStateChainGateway _stateChainGateway
    ) external override onlyGovernor nzAddr(address(_stateChainGateway)) {
        address oldStateChainGateway = address(stateChainGateway);
        stateChainGateway = _stateChainGateway;
        emit StateChainGatewayUpdated(oldStateChainGateway, address(_stateChainGateway));
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

    /// @dev    Getter function for the TokenVesting contract
    function getStateChainGateway() external view override returns (IStateChainGateway) {
        return stateChainGateway;
    }

    /// @dev    Getter function for the governor address
    function getGovernor() external view override returns (address) {
        return governor;
    }

    /// @notice Ensure that the caller is the governor address.
    modifier onlyGovernor() {
        require(msg.sender == governor, "SCGRef: not the governor");
        _;
    }
}
