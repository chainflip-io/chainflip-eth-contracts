pragma solidity ^0.8.0;

import "./Deployer.sol";

contract TestEchidna is Deployer {
    uint256 internal constant pubKeyX = 22479114112312168431982914496826057754130808976066989807481484372215659188398;
    uint8 internal constant pubKeyYParity = 1;
    uint256 internal constant MIN_STAKE = 1000 * E_18;
    uint256 internal constant INIT_SUPPLY = 9 * 10**7 * E_18;
    uint256 internal constant NUM_GENESIS_VALIDATORS = 5;
    uint256 internal constant GENESIS_STAKE = 5000 * E_18;
    address internal constant GOV_KEY = address(1);
    address internal constant COMM_KEY = address(2);

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

    function echidna_suspended() external returns (bool) {
        return v.getSuspendedState() == sm.getSuspendedState() && sm.getSuspendedState() == false;
    }

    function echidna_guardDisabled() external returns (bool) {
        return v.getCommunityGuard() == sm.getCommunityGuard() && sm.getCommunityGuard() == false;
    }

    function echidna_aggKey() external returns (bool) {
        return km.getAggregateKey().pubKeyX == pubKeyX && km.getAggregateKey().pubKeyYParity == pubKeyYParity;
    }

    function echidna_govKey() external returns (bool) {
        return km.getGovernanceKey() == GOV_KEY;
    }

    function echidna_commKey() external returns (bool) {
        return km.getCommunityKey() == COMM_KEY;
    }

    function echidna_minStake() external returns (bool) {
        return sm.getMinimumStake() == MIN_STAKE;
    }

    // No signature has been validated
    function echidna_lastValidateTime() external returns (bool) {
        return _lastValidateTime == km.getLastValidateTime();
    }

    function echidna_whitelistSet() external returns (bool) {
        return km.canConsumeKeyNonceSet() == true;
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

    function checkwhitelistAddrs() external {
        assert(km.getNumberWhitelistedAddresses() == 4);
        for (uint256 i = 0; i < whitelist.length; i++) {
            assert(km.canConsumeKeyNonce(whitelist[i]) == true);
        }
    }

    // Proxy for a signed function
    // Assert if the call is not reverted
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
