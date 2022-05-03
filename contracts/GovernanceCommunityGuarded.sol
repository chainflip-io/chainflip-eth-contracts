pragma solidity ^0.8.0;

import "./interfaces/IGovernanceCommunityGuarded.sol";
import "./AggKeyNonceConsumer.sol";
import "./abstract/Shared.sol";

/**
 * @title    GovernanceCommunityGuarded contract
 * @notice   Allows the governor to perform certain actions for the procotol's safety in
 *           case of emergency. The aim is to allow the governor to suspend execution of
 *           critical functions.
 *           Also, it allows the CommunityKey to safeguard certain functions so the
 *           governor can execute them iff the communityKey allows it.
 *
 * @author   albert-llimos (Albert Llimos)
 */
abstract contract GovernanceCommunityGuarded is Shared, IGovernanceCommunityGuarded {
    /// @dev    Community key - address
    address private _communityKey;

    /// @dev    Community Guard Disabled
    bool private _communityGuardDisabled;

    /// @dev    Whether execution is suspended
    bool private _suspended = false;

    constructor(address communityKey) nzAddr(communityKey) {
        _communityKey = communityKey;
    }

    /**
     * @notice  Get the governor's address. The contracts inheriting this (StakeManager and Vault)
     *          get the governor's address from the KeyManager through the AggKeyNonceConsumer's
     *          inheritance. Therefore, the implementation of this function must be left
     *          to the children. This is a workaround since the isGovernor modifier can't be
     *          made virtual. This contract needs to be marked as abstract.
     * @return  The governor's address
     */
    function getGovernor() internal view virtual returns (address);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Enable Community Guard
     */
    function enableCommunityGuard() external override isCommunityKey isCommunityGuardDisabled {
        _communityGuardDisabled = false;
    }

    /**
     * @notice  Disable Community Guard
     */
    function disableCommunityGuard() external override isCommunityKey isCommunityGuardEnabled{
        _communityGuardDisabled = true;
    }

    /**
     * @notice  Update the Community Key. Can only be called by the current Community Key.
     * @param newCommunityKey   New Community key address.
     */
    function updateCommunityKey(address newCommunityKey) external override isCommunityKey nzAddr(newCommunityKey) {
        _communityKey = newCommunityKey;
    }

    /**
     * @notice Can be used to suspend contract execution - only executable by
     * governance and only to be used in case of emergency.
     */
    function suspend() external override isGovernor isNotSuspended {
        _suspended = true;
    }

    /**
     * @notice      Resume contract execution
     */
    function resume() external override isGovernor isSuspended {
        _suspended = false;
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

    /**
     * @notice  Get suspended state
     * @return  The suspended state
     */
    function getSuspendedState() external view override returns (bool) {
        return _suspended;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                         Modifiers                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Ensure that the caller is the Community Key address.
    modifier isCommunityKey() {
        require(msg.sender == _communityKey, "Governance: not Community Key");
        _;
    }

    /// @dev    Check that community has disabled the community guard.
    modifier isCommunityGuardDisabled() {
        require(_communityGuardDisabled, "Governance: community guard not disabled");
        _;
    }

    /// @dev    Check that community has disabled the community guard.
    modifier isCommunityGuardEnabled() {
        require(!_communityGuardDisabled, "Governance: community guard disabled");
        _;
    }

    /// @notice Ensure that the caller is the governor address. Calls the getGovernor
    ///         function which is implemented by the children.
    modifier isGovernor() {
        require(msg.sender == getGovernor(), "Governance: not governor");
        _;
    }

    // @notice Check execution is suspended
    modifier isSuspended() {
        require(_suspended, "Governance: not suspended");
        _;
    }

    // @notice Check execution is not suspended
    modifier isNotSuspended() {
        require(!_suspended, "Governance: suspended");
        _;
    }
}
