pragma solidity ^0.8.0;

import "../contracts/Deployer.sol";

contract TestEchidnaGovComm is Deployer {
    address internal govKey = address(this);
    address internal commKey = address(this);
    uint256 internal minStake = 1000 * E_18;

    // Echidna requires that no parameters are passed to the constructor so we need to set
    // constants for the deployments of the contracts
    constructor()
        Deployer(PUBKEYX, PUBKEYYPARITY, minStake, INIT_SUPPLY, NUM_GENESIS_VALIDATORS, GENESIS_STAKE, govKey, commKey)
    {}

    // PROPERTY TESTING - need to run echidna in testMode: "property"

    // No function call that requires signing should pass the signature check - checking that contract state
    // remains the same after the function calls instead of checking function reverts one by one. This is because
    // ´echidna_revert_*` takes no arguments.
    // This contract acts as the governance and community Key.

    /* solhint-disable  func-name-mixedcase*/
    function echidna_flipSupply() external returns (bool) {
        return f.totalSupply() == INIT_SUPPLY;
    }

    function echidna_kmReference() external returns (bool) {
        return
            f.getKeyManager() == sm.getKeyManager() &&
            sm.getKeyManager() == v.getKeyManager() &&
            v.getKeyManager() == km;
    }

    function echidna_aggKey() external returns (bool) {
        return km.getAggregateKey().pubKeyX == PUBKEYX && km.getAggregateKey().pubKeyYParity == PUBKEYYPARITY;
    }

    // Gov key changes
    function setGovKeyWithGovKey(address newGovKey) external override {
        km.setGovKeyWithGovKey(newGovKey);
        govKey = newGovKey;
        assert(
            sm.getGovernor() == v.getGovernor() &&
                v.getGovernor() == km.getGovernanceKey() &&
                km.getGovernanceKey() == govKey
        );
    }

    // ASSERTION TESTING - need to run echidna in testMode: "assertion"

    // Comm key changes
    function setCommKeyWithCommKey(address newCommKey) external override {
        km.setCommKeyWithCommKey(newCommKey);
        commKey = newCommKey;
        assert(
            sm.getCommunityKey() == v.getCommunityKey() &&
                v.getCommunityKey() == km.getCommunityKey() &&
                km.getCommunityKey() == commKey
        );
    }

    // No signature has been validated
    function echidna_lastValidateTime() external returns (bool) {
        return _lastValidateTime == km.getLastValidateTime();
    }

    function echidna_whitelistSet() external returns (bool) {
        return km.canConsumeKeyNonceSet();
    }

    // Suspend and resume functions
    function suspendVault() external override {
        v.suspend();
        assert(v.getSuspendedState() == true);
    }

    function suspendStakeManager() external override {
        sm.suspend();
        assert(sm.getSuspendedState() == true);
    }

    function resumeVault() external override {
        v.resume();
        assert(v.getSuspendedState() == false);
    }

    function resumeStakeManager() external override {
        sm.resume();
        assert(sm.getSuspendedState() == false);
    }

    // Community Guard
    function enableCommunityGuardVault() external override {
        v.enableCommunityGuard();
        assert(v.getCommunityGuardDisabled() == false);
    }

    function disableCommunityGuardVault() external override {
        v.disableCommunityGuard();
        assert(v.getCommunityGuardDisabled() == true);
    }

    function enableCommunityGuardStakeManager() external override {
        v.enableCommunityGuard();
        assert(v.getCommunityGuardDisabled() == false);
    }

    function disableCommunityGuardStakeManager() external override {
        sm.disableCommunityGuard();
        assert(sm.getCommunityGuardDisabled() == true);
    }

    function setMinStake(uint256 newMinStake) external override {
        sm.setMinStake(newMinStake);
        minStake = newMinStake;
        assert(sm.getMinimumStake() == minStake);
    }

    // xCalls enabled
    function enablexCalls() external override {
        v.enablexCalls();
        assert(v.getxCallsEnabled() == true);
    }

    function disablexCalls() external override {
        v.disablexCalls();
        assert(v.getxCallsEnabled() == false);
    }

    function checkwhitelistAddrs() external {
        assert(km.getNumberWhitelistedAddresses() == 4);
        for (uint256 i = 0; i < whitelist.length; i++) {
            assert(km.canConsumeKeyNonce(whitelist[i]) == true);
        }
    }

    // ´echidna_revert_*´ takes no parameters and expects a revert
    // Different calls expected to revert should be in different echidna_revert_ functions
    // since echidna checks that the call is reverted at any point

    // Proxy for a signed function - Assert if the call is not reverted
    function allBatch_revert(
        SigData calldata sigData,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    ) external {
        try v.allBatch(sigData, fetchParamsArray, transferParamsArray) {
            assert(false);
        } catch {
            assert(true);
        }
    }
    /* solhint-enable  func-name-mixedcase*/
}
