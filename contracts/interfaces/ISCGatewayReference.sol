pragma solidity ^0.8.0;

import "./IStateChainGateway.sol";

interface ISCGatewayReference {
    event StateChainGatewayUpdated(address oldStateChainGateway, address newStateChainGateway);
    event GovernorTransferred(address oldGovernor, address newGovernor);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function updateStateChainGateway(IStateChainGateway stateChainGateway_) external;

    function transferGovernor(address _governor) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getStateChainGateway() external view returns (IStateChainGateway);

    function getGovernor() external view returns (address);
}
