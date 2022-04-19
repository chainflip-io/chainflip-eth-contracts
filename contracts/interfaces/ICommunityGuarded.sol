pragma solidity ^0.8.0;

import "./IShared.sol";

/**
 * @title    CommunityGuarded interface
 * @author   albert-llimos (Albert Llimos)
 */

interface ICommunityGuarded is IShared {
    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////
    /**
     * @notice  Set the Community Guard state
     * @param communityGuardDisabled   New Community Guard state
     */
    function setCommunityGuard(bool communityGuardDisabled) external;

    /**
     * @notice  Update the Community Key. Can only be called by the current Community Key.
     * @param newCommunityKey   New Community key address.
     */
    function updateCommunityKey(address newCommunityKey) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the Community Key
     * @return  The CommunityKey
     */
    function getCommunityKey() external view returns (address);

    /**
     * @notice  Get the Community Guard state
     * @return  The Community Guard state
     */
    function getCommunityGuard() external view returns (bool);
}
