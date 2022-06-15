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
    // Common constants across tests
    uint256 internal constant E_18 = 10**18;
    uint256 internal constant pubKeyX = 22479114112312168431982914496826057754130808976066989807481484372215659188398;
    uint8 internal constant pubKeyYParity = 1;
    uint256 internal constant MIN_STAKE = 1000 * E_18;
    uint256 internal constant INIT_SUPPLY = 9 * 10**7 * E_18;
    uint256 internal constant NUM_GENESIS_VALIDATORS = 5;
    uint256 internal constant GENESIS_STAKE = 5000 * E_18;

    // Common storage variables across tests
    address[] whitelist;
    uint256 internal _lastValidateTime;

    // Tests will pass the deploying values - deploying contracts mimicking deploy.py
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
