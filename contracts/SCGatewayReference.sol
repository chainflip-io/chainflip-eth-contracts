pragma solidity ^0.8.0;

import "./interfaces/ISCGatewayReference.sol";
import "./abstract/Shared.sol";

/**
 * @title StateChainGatewayReference
 * @dev A contract that holds a reference to the StateChainGateway contract. This is for the
 *      tokenVesting contracts so the governor don't have to update dozens of references making
 *      calls from a multisig in case of the StateChainGateway contract being upgraded.
 *      The governor address will be the same as the revoker address in the TokenVesting contract.
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
        emit StateChainGatewayUpdated(address(stateChainGateway), address(_stateChainGateway));
        stateChainGateway = _stateChainGateway;
    }

    /// @dev    Allow the governor to transfer governance to a new address in case of need
    function updateGovernor(address _governor) external override onlyGovernor nzAddr(_governor) {
        emit GovernorUpdated(governor, _governor);
        governor = _governor;
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
