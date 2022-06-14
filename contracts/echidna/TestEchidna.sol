pragma solidity ^0.8.0;

import "../Vault.sol";
import "../FLIP.sol";
import "../KeyManager.sol";
import "../StakeManager.sol";

import "./KeyManagerEchidna.sol";
import "./StakeManagerEchidna.sol";
import "./VaultEchidna.sol";
import "./FLIPEchidna.sol";

contract TestEchidna is IShared, KeyManagerEchidna, StakeManagerEchidna, FLIPEchidna, VaultEchidna {
    uint256 private constant pubKeyX = 22479114112312168431982914496826057754130808976066989807481484372215659188398;
    uint8 private constant pubKeyYParity = 1;
    uint256 private constant E_18 = 10**18;
    uint256 private constant MIN_STAKE = 1000 * E_18;
    uint256 private constant INIT_SUPPLY = 9 * 10**7 * E_18;
    uint256 private constant NUM_GENESIS_VALIDATORS = 5;
    uint256 private constant GENESIS_STAKE = 5000 * E_18;
    address private constant GOV_KEY = address(1);
    address private constant COMM_KEY = address(2);
    address[] whitelist;

    uint256 private _lastValidateTime;

    // Echidna requires that no paramters are passed to the constructor so
    // deploying contracts with fixed parameters - mimic deploy.py
    constructor() {
        // Deploy the KeyManager contract
        // Setting both govKey and commKey to an address that won't be used
        // We can do another test setting govKey and commkey to this address
        km = new KeyManager(Key(pubKeyX, pubKeyYParity), GOV_KEY, COMM_KEY);
        v = new Vault(km);
        sm = new StakeManager(km, MIN_STAKE);
        f = new FLIP(INIT_SUPPLY, NUM_GENESIS_VALIDATORS, GENESIS_STAKE, address(sm), km);
        sm.setFlip(FLIP(address(f)));
        whitelist = [address(v), address(sm), address(km), address(f)];
        km.setCanConsumeKeyNonce(whitelist);
        _lastValidateTime = block.timestamp;
    }

    // Property testing
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

    // No function call that requires signing should pass the signature check
    function echidna_lastValidateTime() external returns (bool) {
        return _lastValidateTime == km.getLastValidateTime();
    }

    function echidna_whitelistSet() external returns (bool) {
        return km.canConsumeKeyNonceSet() == true;
    }

    function checkwhitelistAddrs() external {
        assert(km.getNumberWhitelistedAddresses() == 4);
        address[4] memory whitelist = [address(v), address(sm), address(km), address(f)];
        for (uint256 i = 0; i < whitelist.length; i++) {
            assert(km.canConsumeKeyNonce(whitelist[i]) == true);
        }
    }

    // ´echidna_revert_*´ takes no parameters and expects a revert
    // Different calls expected to revert should be in different echidna_revert_ functions
    // since echidna checks that the call is reverted at any point
    function echidna_revert_resume() external {
        v.resume();
    }

    function echidna_revert_disableCommGuard() external {
        v.disableCommunityGuard();
    }
}
