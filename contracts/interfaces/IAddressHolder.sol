// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IAddressHolder {
    event StateChainGatewayUpdated(address oldStateChainGateway, address newStateChainGateway);
    event StakingAddressesUpdated(
        address oldStMinter,
        address oldStBurner,
        address oldStFLIP,
        address newStMinter,
        address newStBurner,
        address newStFLIP
    );
    event GovernorTransferred(address oldGovernor, address newGovernor);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function updateStateChainGateway(address _stateChainGateway) external;

    function updateStakingAddresses(address _stMinter, address _stBurner, address _stFLIP) external;

    function transferGovernor(address _governor) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getStateChainGateway() external view returns (address);

    function getStakingAddress() external view returns (address);

    function getUnstakingAddresses() external view returns (address, address);

    function getStFlip() external view returns (address);

    function getGovernor() external view returns (address);
}
