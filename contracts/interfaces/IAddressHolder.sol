// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IAddressHolder {
    event ReferenceAddressUpdated(address oldReferenceAddress, address newReferenceAddress);
    event GovernorTransferred(address oldGovernor, address newGovernor);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function updateReferenceAddress(address _referenceAddress) external;

    function transferGovernor(address _governor) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getReferenceAddress() external view returns (address);

    function getGovernor() external view returns (address);
}
