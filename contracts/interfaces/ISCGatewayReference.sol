pragma solidity ^0.8.0;

import "./IStateChainGateway.sol";

interface ISCGatewayReference {
    function updateStateChainGateway(IStateChainGateway stateChainGateway_) external;

    function updateGovernor(address _governor) external;

    function getStateChainGateway() external view returns (IStateChainGateway);
}
