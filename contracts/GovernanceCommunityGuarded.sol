pragma solidity ^0.8.0;

import "./interfaces/IGovernanceCommunityGuarded.sol";
import "./AggKeyNonceConsumer.sol";
import "./abstract/Shared.sol";

/**
 * @title    GovernanceCommunityGuarded contract
 * @notice   Allows the governor to perform certain actions for the procotol's safety.
 *           It allows the governor to suspend execution in case of emergency. This shall
 *           stop the execution of functions that require an AggKey signature in the child's
 *           contract. Notice that this contract inherits from AggKeyNonceConsumer, so it
 *           allows the child's contract to validate signatures.
 *           Finally, it provides the child's contract to have the ability to safeguard
 *           certain functions, allowing the governor to execute them iff the community
 *           key allows it.
 *
 * @author   albert-llimos (Albert Llimos)
 */
contract GovernanceCommunityGuarded is AggKeyNonceConsumer, IGovernanceCommunityGuarded {
    /// @dev    Community key - address
    address private _communityKey;

    /// @dev    Community Guard Disabled
    bool private _communityGuardDisabled;

    /// @dev    Whether execution is suspended
    bool private _suspended = false;

    constructor(IKeyManager keyManager, address communityKey) nzAddr(communityKey) AggKeyNonceConsumer(keyManager) {
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

    /// @notice Ensure that the caller is the KeyManager's governor address.
    modifier isGovernor() {
        require(msg.sender == _getKeyManager().getGovernanceKey(), "Staking: not governor");
        _;
    }

    // @notice Check execution is suspended
    modifier isSuspended() {
        require(_suspended, "Staking: not suspended");
        _;
    }

    // @notice Check execution is not suspended
    modifier isNotSuspended() {
        require(!_suspended, "Staking: suspended");
        _;
    }
}
