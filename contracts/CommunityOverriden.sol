pragma solidity ^0.8.0;

import "./interfaces/ICommunityOverriden.sol";
import "./abstract/Shared.sol";

/**
 * @title    CommunityOverriden contract
 * @notice   Allows for community to override governor actions. The community
 *           address is set in the constructor and can only be updated by the
 *           community address itself.
 * @author   albert-llimos (Albert Llimos)
 */
contract CommunityOverriden is Shared, ICommunityOverriden {
    /// @dev    Community key - address
    address private _communityKey;

    /// @dev    Override governor action
    bool private _overrideAction = true;

    constructor(address communityKey) nzAddr(communityKey) {
        _communityKey = communityKey;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Set the Community Key override Action
     * @param overrideAction   New Override action
     */
    function setOverrideAction(bool overrideAction) external override isCommunityKey {
        _overrideAction = overrideAction;
    }

    /**
     * @notice  Update the Community Key. Can only be called by the current Community Key.
     * @param newCommunityKey   New Community key address.
     */
    function updateCommunityKey(address newCommunityKey) external override isCommunityKey nzAddr(newCommunityKey) {
        _communityKey = newCommunityKey;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the Community Key that can override governor actions
     * @return  The CommunityKey
     */
    function getCommunityKey() external view override returns (address) {
        return _communityKey;
    }

    /**
     * @notice  Get the Community Key override's Action state
     * @return  The CommunityKey override's Action state
     */
    function getCommunityKeyOverride() external view override returns (bool) {
        return _overrideAction;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                         Modifiers                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Ensure that the caller is the Community Key address.
    modifier isCommunityKey() {
        require(msg.sender == _communityKey, "Community: not Community Key");
        _;
    }

    /// @dev    Check that community doesn't override the function call.
    modifier isNotCommunityOverriden() {
        require(!_overrideAction, "Community: overriden by community");
        _;
    }
}
