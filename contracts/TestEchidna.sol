pragma solidity ^0.8.0;

import "./Vault.sol";
import "./FLIP.sol";
import "./KeyManager.sol";
import "./StakeManager.sol";
import "./interfaces/IShared.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IFLIP.sol";
import "./interfaces/IVault.sol";

contract TestEchidna is IShared{

    uint256 private constant pubKeyX = 22479114112312168431982914496826057754130808976066989807481484372215659188398;
    uint8 private constant  pubKeyYParity = 1;
    uint256 private constant E_18 = 10**18;
    uint256 private constant MIN_STAKE = 1000 * E_18;
    uint256 private constant INIT_SUPPLY = 9 * 10**7 * E_18;
    uint256 private constant NUM_GENESIS_VALIDATORS = 5;
    uint256 private constant GENESIS_STAKE = 5000 * E_18;



    IKeyManager private km;
    IFLIP private f;
    IVault private v;
    IStakeManager private sm;

    uint256 private _lastValidateTime;

    // Deploy contracts with fixed parameters - mimic deploy.py
    // Echidna requires that no paramters are passed to the constructor
    constructor() {
        // Deploy the KeyManager contract - setting random non-zero addresses as gov and communityKey
        km = new KeyManager(Key(pubKeyX, pubKeyYParity),address(1), address(2));
        v = new Vault(km);
        sm = new StakeManager(km, MIN_STAKE);
        f = new FLIP(INIT_SUPPLY, NUM_GENESIS_VALIDATORS ,GENESIS_STAKE, address(sm), km);
        _lastValidateTime = block.timestamp;
    }

    // function setNewTime(uint256 newTime) external{
    //     km.setLastValidateTime(newTime);
    // }

    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber,
        address staker
    ) external {
        f.updateFlipSupply(sigData, newTotalSupply, stateChainBlockNumber, staker);
    }


    function echidna_pass() external pure returns (bool) {
        return true;
    }

    // No function call that requires signing should pass the signature check
    function echidna_last() external returns (bool) {
        return _lastValidateTime == km.getLastValidateTime();
    }
}