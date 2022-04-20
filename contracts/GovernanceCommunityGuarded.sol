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

    /**
     * @notice  Get the governor's address. To be overriden depending on the
     *          contract's implementation
     * @return  The governor's address
     */
    function getGovernor() internal view virtual returns (address);

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
        require(_communityGuardDisabled, "Governance: guard not disabled by community");
        _;
    }

    /// @notice Ensure that the caller is the KeyManager's governor address.
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
