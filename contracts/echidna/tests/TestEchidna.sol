pragma solidity ^0.8.0;

import "../contracts/Deployer.sol";

contract TestEchidna is Deployer {
    address internal govKey = address(1);
    address internal commKey = address(2);
    uint256 internal minStake = 1000 * E_18;

    // Echidna requires that no parameters are passed to the constructor so we need to set
    // constants for the deployments of the contracts
    constructor()
        Deployer(PUBKEYX, PUBKEYYPARITY, minStake, INIT_SUPPLY, NUM_GENESIS_VALIDATORS, GENESIS_STAKE, govKey, commKey)
    {}

    // PROPERTY TESTING - need to run echidna in testMode: "property"

    // No function call that requires signing should pass the signature check - checking that contract state
    // remains the same after the function calls instead of checking function reverts one by one. This is because
    // ´echidna_revert_*` takes no arguments. Also no call from the governor is made.

    /* solhint-disable  func-name-mixedcase*/
    function echidna_flipSupply() external view returns (bool) {
        return f.totalSupply() == INIT_SUPPLY;
    }

    function echidna_kmReference() external view returns (bool) {
        return
            f.getKeyManager() == sm.getKeyManager() &&
            sm.getKeyManager() == v.getKeyManager() &&
            v.getKeyManager() == km;
    }

    function echidna_govKey() external view returns (bool) {
        return
            sm.getGovernor() == v.getGovernor() &&
            v.getGovernor() == km.getGovernanceKey() &&
            km.getGovernanceKey() == govKey;
    }

    function echidna_commKey() external view returns (bool) {
        return
            sm.getCommunityKey() == v.getCommunityKey() &&
            v.getCommunityKey() == km.getCommunityKey() &&
            km.getCommunityKey() == commKey;
    }

    function echidna_aggKey() external view returns (bool) {
        return km.getAggregateKey().pubKeyX == PUBKEYX && km.getAggregateKey().pubKeyYParity == PUBKEYYPARITY;
    }

    function echidna_suspended() external view returns (bool) {
        return v.getSuspendedState() == sm.getSuspendedState() && sm.getSuspendedState() == false;
    }

    function echidna_guardDisabled() external view returns (bool) {
        return
            v.getCommunityGuardDisabled() == sm.getCommunityGuardDisabled() && sm.getCommunityGuardDisabled() == false;
    }

    function echidna_minStake() external view returns (bool) {
        return sm.getMinimumStake() == minStake;
    }

    function echidna_swapsEnabled() external view returns (bool) {
        return !v.getxCallsEnabled();
    }

    // No signature has been validated
    function echidna_lastValidateTime() external view returns (bool) {
        return _lastValidateTime == km.getLastValidateTime();
    }

    function echidna_whitelistSet() external view returns (bool) {
        return km.canConsumeKeyNonceSet();
    }

    // ´echidna_revert_*´ takes no parameters and expects a revert
    // Different calls expected to revert should be in different echidna_revert_ functions
    // since echidna checks that the call is reverted at any point

    // Adding some proxy functions for community and governance keys that should revert
    function echidna_revert_resume() external {
        v.resume();
    }

    function echidna_revert_pause() external {
        v.suspend();
    }

    function echidna_revert_disableCommGuard() external {
        v.disableCommunityGuard();
    }

    function echidna_revert_enableCommGuard() external {
        v.enableCommunityGuard();
    }

    // ASSERTION TESTING - need to run echidna in testMode: "assertion"

    function checkwhitelistAddrs() external view {
        assert(km.getNumberWhitelistedAddresses() == 4);
        for (uint256 i = 0; i < whitelist.length; i++) {
            assert(km.canConsumeKeyNonce(whitelist[i]) == true);
        }
    }

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

    function echidna_flipBalance() external view returns (bool) {
        return f.balanceOf(address(sm)) == NUM_GENESIS_VALIDATORS * GENESIS_STAKE;
    }
    /* solhint-enable  func-name-mixedcase*/
}
