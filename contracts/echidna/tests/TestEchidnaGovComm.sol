pragma solidity ^0.8.0;

import "../contracts/Deployer.sol";

contract TestEchidnaGovComm is Deployer {
    address internal GOV_KEY = address(this);
    address internal COMM_KEY = address(this);
    uint256 internal MIN_STAKE = 1000 * E_18;

    // Echidna requires that no parameters are passed to the constructor so we need to set
    // constants for the deployments of the contracts
    constructor()
        Deployer(
            pubKeyX,
            pubKeyYParity,
            MIN_STAKE,
            INIT_SUPPLY,
            NUM_GENESIS_VALIDATORS,
            GENESIS_STAKE,
            GOV_KEY,
            COMM_KEY
        )
    {}

    // PROPERTY TESTING - need to run echidna in testMode: "property"

    // No function call that requires signing should pass the signature check - checking that contract state
    // remains the same after the function calls instead of checking function reverts one by one. This is because
    // ´echidna_revert_*` takes no arguments. Also no call from the governor is made.
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
        return km.getAggregateKey().pubKeyX == pubKeyX && km.getAggregateKey().pubKeyYParity == pubKeyYParity;
    }

    // Gov key changes
    function setGovKeyWithGovKey(address newGovKey) external override {
        km.setGovKeyWithGovKey(newGovKey);
        GOV_KEY = newGovKey;
        assert(
            sm.getGovernor() == v.getGovernor() &&
                v.getGovernor() == km.getGovernanceKey() &&
                km.getGovernanceKey() == GOV_KEY
        );
    }

    // ASSERTION TESTING - need to run echidna in testMode: "assertion"

    // Comm key changes
    function setCommKeyWithCommKey(address newCommKey) external override {
        km.setCommKeyWithCommKey(newCommKey);
        COMM_KEY = newCommKey;
        assert(
            sm.getCommunityKey() == v.getCommunityKey() &&
                v.getCommunityKey() == km.getCommunityKey() &&
                km.getCommunityKey() == COMM_KEY
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
        assert(v.getCommunityGuard() == false);
    }

    function disableCommunityGuardVault() external override {
        v.disableCommunityGuard();
        assert(v.getCommunityGuard() == true);
    }

    function enableCommunityGuardStakeManager() external override {
        v.enableCommunityGuard();
        assert(v.getCommunityGuard() == false);
    }

    function disableCommunityGuardStakeManager() external override {
        sm.disableCommunityGuard();
        assert(sm.getCommunityGuard() == true);
    }

    function setMinStake(uint256 newMinStake) external override {
        sm.setMinStake(newMinStake);
        MIN_STAKE = newMinStake;
        assert(sm.getMinimumStake() == MIN_STAKE);
    }

    // Swaps enabled
    function enableSwaps() external override {
        v.enableSwaps();
        assert(v.getSwapsEnabled() == true);
    }

    function disableSwaps() external override {
        v.disableSwaps();
        assert(v.getSwapsEnabled() == false);
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
        bytes32[] calldata fetchSwapIDs,
        IERC20[] calldata fetchTokens,
        IERC20[] calldata tranTokens,
        address payable[] calldata tranRecipients,
        uint256[] calldata tranAmounts
    ) external {
        try v.allBatch(sigData, fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts) {
            assert(false);
        } catch {
            assert(true);
        }
    }
}
