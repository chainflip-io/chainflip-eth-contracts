pragma solidity ^0.8.0;

import "./IShared.sol";

/**
 * @title    AggKeyNonceConsumer interface
 * @author   albert-llimos (Albert Llimos)
 */

interface ICommunityOverriden is IShared {
    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////
    /**
     * @notice  Set the Community Key override Action
     * @param overrideAction   New Override action
     */
    function setOverrideAction(bool overrideAction) external;

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
     * @notice  Get the Community Key that can override governor actions
     * @return  The CommunityKey
     */
    function getCommunityKey() external view returns (address);

    /**
     * @notice  Get the Community Key override's Action state
     * @return  The CommunityKey override's Action state
     */
    function getCommunityKeyOverride() external view returns (bool);
}
