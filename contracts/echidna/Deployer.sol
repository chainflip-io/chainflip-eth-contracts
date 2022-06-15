pragma solidity ^0.8.0;

import "../Vault.sol";
import "../FLIP.sol";
import "../KeyManager.sol";
import "../StakeManager.sol";

import "./KeyManagerEchidna.sol";
import "./StakeManagerEchidna.sol";
import "./VaultEchidna.sol";
import "./FLIPEchidna.sol";

contract Deployer is KeyManagerEchidna, StakeManagerEchidna, FLIPEchidna, VaultEchidna {
    uint256 internal constant E_18 = 10**18;

    address[] whitelist;
    uint256 internal _lastValidateTime;

    // Echidna requires that no paramters are passed to the constructor so
    // deploying contracts with fixed parameters - mimic deploy.py
    constructor(
        uint256 pubKeyX,
        uint8 pubKeyYParity,
        uint256 MIN_STAKE,
        uint256 INIT_SUPPLY,
        uint256 NUM_GENESIS_VALIDATORS,
        uint256 GENESIS_STAKE,
        address GOV_KEY,
        address COMM_KEY
    ) {
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
}
