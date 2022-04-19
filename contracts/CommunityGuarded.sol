pragma solidity ^0.8.0;

import "./interfaces/ICommunityGuarded.sol";
import "./abstract/Shared.sol";

/**
 * @title    CommunityGuarded contract
 * @notice   Allows for community to guard functions, preventing the governor
 *           from calling them. The community address is set in the constructor
 *           and can only be updated by the community address itself.
 * @author   albert-llimos (Albert Llimos)
 */
contract CommunityGuarded is Shared, ICommunityGuarded {
    /// @dev    Community key - address
    address private _communityKey;

    /// @dev    Community Guard Disabled
    bool private _communityGuardDisabled;

    constructor(address communityKey) nzAddr(communityKey) {
        _communityKey = communityKey;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Set the Community Guard state
     * @param communityGuardDisabled   New Community Guard state
     */
    function setCommunityGuard(bool communityGuardDisabled) external override isCommunityKey {
        _communityGuardDisabled = communityGuardDisabled;
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
     * @notice  Get the Community Key
     * @return  The CommunityKey
     */
    function getCommunityKey() external view override returns (address) {
        return _communityKey;
    }

    /**
     * @notice  Get the Community Guard state
     * @return  The Community Guard state
     */
    function getCommunityGuard() external view override returns (bool) {
        return _communityGuardDisabled;
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

    /// @dev    Check that community has disabled the community guard.
    modifier isCommunityGuardDisabled() {
        require(_communityGuardDisabled, "Community: guard not disabled by community");
        _;
    }
}
