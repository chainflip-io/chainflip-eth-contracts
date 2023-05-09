pragma solidity ^0.8.0;

import "./interfaces/ISCGatewayReference.sol";

/**
 * @title StateChainGatewayReference
 * @dev A contract that holds a reference to the StateChainGateway contract. This is for the
 *      tokenVesting contracts so the governor don't have to update dozens of references making
 *      calls from a multisig in case of the StateChainGateway contract being upgraded.
 *      The governor address will be the same as the revoker address in the TokenVesting contract.
 */
contract SCGatewayReference is ISCGatewayReference {
    address public governor;

    IStateChainGateway private stateChainGateway;

    constructor(address _governor, IStateChainGateway _stateChainGateway) {
        governor = _governor;
        stateChainGateway = _stateChainGateway;
    }

    /// @dev    Update the reference to the StateChainGateway contract
    function updateStateChainGateway(IStateChainGateway _stateChainGateway) external override onlyGovernor {
        stateChainGateway = _stateChainGateway;
    }

    /// @dev    Allow the governor to transfer governance to a new address in case of need
    function updateGovernor(address _governor) external override onlyGovernor {
        governor = _governor;
    }

    /// @dev    Getter function for the TokenVesting contract
    function getStateChainGateway() external view override returns (IStateChainGateway) {
        return stateChainGateway;
    }

    /// @notice Ensure that the caller is the governor address.
    modifier onlyGovernor() {
        require(msg.sender == governor, "SCGRef: not the governor");
        _;
    }
}
