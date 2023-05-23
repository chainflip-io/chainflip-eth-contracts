// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../contracts/DeployerEchidna.sol";

contract TestEchidna is DeployerEchidna {
    address internal govKey = address(1);
    address internal commKey = address(2);
    uint256 internal minFunding = 1000 * E_18;

    // Echidna requires that no parameters are passed to the constructor so we need to set
    // constants for the deployments of the contracts
    constructor()
        DeployerEchidna(
            Key(PUBKEYX, PUBKEYYPARITY),
            govKey,
            commKey,
            minFunding,
            INIT_SUPPLY,
            NUM_GENESIS_VALIDATORS,
            GENESIS_STAKE
        )
    {}

    // PROPERTY TESTING - need to run echidna in testMode: "property"

    // No function call that requires signing should pass the signature check - checking that contract state
    // remains the same after the function calls instead of checking function reverts one by one. This is because
    // ´echidna_revert_*` takes no arguments. Also no call from the governor is made.

    /* solhint-disable  func-name-mixedcase*/
    function echidna_flipSupply() external view returns (bool) {
        return flip.totalSupply() == INIT_SUPPLY;
    }

    function echidna_kmReference() external view returns (bool) {
        return stateChainGateway.getKeyManager() == vault.getKeyManager() && vault.getKeyManager() == keyManager;
    }

    function echidna_govKey() external view returns (bool) {
        return
            stateChainGateway.getGovernor() == vault.getGovernor() &&
            vault.getGovernor() == keyManager.getGovernanceKey() &&
            keyManager.getGovernanceKey() == govKey;
    }

    function echidna_commKey() external view returns (bool) {
        return
            stateChainGateway.getCommunityKey() == vault.getCommunityKey() &&
            vault.getCommunityKey() == keyManager.getCommunityKey() &&
            keyManager.getCommunityKey() == commKey;
    }

    function echidna_aggKey() external view returns (bool) {
        return
            keyManager.getAggregateKey().pubKeyX == PUBKEYX &&
            keyManager.getAggregateKey().pubKeyYParity == PUBKEYYPARITY;
    }

    function echidna_suspended() external view returns (bool) {
        return
            vault.getSuspendedState() == stateChainGateway.getSuspendedState() &&
            stateChainGateway.getSuspendedState() == false;
    }

    function echidna_guardDisabled() external view returns (bool) {
        return
            vault.getCommunityGuardDisabled() == stateChainGateway.getCommunityGuardDisabled() &&
            stateChainGateway.getCommunityGuardDisabled() == false;
    }

    function echidna_minFunding() external view returns (bool) {
        return stateChainGateway.getMinimumFunding() == minFunding;
    }

    // No signature has been validated
    function echidna_lastValidateTime() external view returns (bool) {
        return _lastValidateTime == keyManager.getLastValidateTime();
    }

    // ´echidna_revert_*´ takes no parameters and expects a revert
    // Different calls expected to revert should be in different echidna_revert_ functions
    // since echidna checks that the call is reverted at any point

    // Adding some proxy functions for community and governance keys that should revert
    function echidna_revert_resume() external {
        vault.resume();
    }

    function echidna_revert_pause() external {
        vault.suspend();
    }

    function echidna_revert_disableCommGuard() external {
        vault.disableCommunityGuard();
    }

    function echidna_revert_enableCommGuard() external {
        vault.enableCommunityGuard();
    }

    // ASSERTION TESTING - need to run echidna in testMode: "assertion"

    // Proxies for a signed function - Assert if the call is not reverted
    function executeRedemption_revert(bytes32 nodeID) external {
        try stateChainGateway.executeRedemption(nodeID) {
            assert(false);
        } catch {
            assert(true);
        }
    }

    function allBatch_revert(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    ) external {
        try vault.allBatch(sigData, deployFetchParamsArray, fetchParamsArray, transferParamsArray) {
            assert(false);
        } catch {
            assert(true);
        }
    }

    function executexSwapAndCall_revert(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external {
        try vault.executexSwapAndCall(sigData, transferParams, srcChain, srcAddress, message) {
            assert(false);
        } catch {
            assert(true);
        }
    }

    function echidna_flipBalance() external view returns (bool) {
        return flip.balanceOf(address(stateChainGateway)) == NUM_GENESIS_VALIDATORS * GENESIS_STAKE;
    }
    /* solhint-enable  func-name-mixedcase*/
}
