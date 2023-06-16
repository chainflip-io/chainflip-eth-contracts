// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IAddressHolder {
    event StateChainGatewayUpdated(address oldStateChainGateway, address newStateChainGateway);
    event GovernorTransferred(address oldGovernor, address newGovernor);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function updateStateChainGateway(address _stateChainGateway) external;

    function transferGovernor(address _governor) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getStateChainGateway() external view returns (address);

    function getGovernor() external view returns (address);
}
