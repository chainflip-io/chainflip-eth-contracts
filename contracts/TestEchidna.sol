pragma solidity ^0.8.0;

import "./Vault.sol";
import "./FLIP.sol";
import "./KeyManager.sol";
import "./StakeManager.sol";
import "./interfaces/IShared.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IFLIP.sol";
import "./interfaces/IVault.sol";

contract TestEchidna is IShared {
    uint256 private constant pubKeyX = 22479114112312168431982914496826057754130808976066989807481484372215659188398;
    uint8 private constant pubKeyYParity = 1;
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

    // Echidna requires that no paramters are passed to the constructor so
    // deploying contracts with fixed parameters - mimic deploy.py
    constructor() {
        // Deploy the KeyManager contract
        // Setting gov key as this address for test purposes. Maybe later set this to a real gov key
        // in another test and test that
        km = new KeyManager(Key(pubKeyX, pubKeyYParity), address(1), address(2));
        v = new Vault(km);
        sm = new StakeManager(km, MIN_STAKE);
        f = new FLIP(INIT_SUPPLY, NUM_GENESIS_VALIDATORS, GENESIS_STAKE, address(sm), km);
        sm.setFlip(FLIP(address(f)));
        _lastValidateTime = block.timestamp;
    }

    // Add all function calls to give visibility to echidna for fuzzing

    // Key Manager

    function setCanConsumeKeyNonce(address[] calldata addrs) external {
        km.setCanConsumeKeyNonce(addrs);
    }

    function updateCanConsumeKeyNonce(
        SigData calldata sigData,
        address[] calldata currentAddrs,
        address[] calldata newAddrs
    ) external {
        km.updateCanConsumeKeyNonce(sigData, currentAddrs, newAddrs);
    }

    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) external {
        km.consumeKeyNonce(sigData, contractMsgHash);
    }

    function setAggKeyWithAggKey(SigData calldata sigData, Key calldata newAggKey) external {
        km.setAggKeyWithAggKey(sigData, newAggKey);
    }

    function setGovKeyWithAggKey(SigData calldata sigData, address newGovKey) external {
        km.setGovKeyWithAggKey(sigData, newGovKey);
    }

    function setGovKeyWithGovKey(address newGovKey) external {
        km.setGovKeyWithGovKey(newGovKey);
    }

    function setCommKeyWithAggKey(SigData calldata sigData, address newCommKey) external {
        km.setCommKeyWithAggKey(sigData, newCommKey);
    }

    function setCommKeyWithCommKey(address newCommKey) external {
        km.setCommKeyWithCommKey(newCommKey);
    }

    function govAction(bytes32 message) external {
        km.govAction(message);
    }

    // Stake Manager

    function setFlip(FLIP flip) external {
        sm.setFlip(flip);
    }

    function stake(
        bytes32 nodeID,
        uint256 amount,
        address returnAddr
    ) external {
        // TODO: Add approve tokens function?
        sm.stake(nodeID, amount, returnAddr);
    }

    function registerClaim(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address staker,
        uint48 expiryTime
    ) external {
        sm.registerClaim(sigData, nodeID, amount, staker, expiryTime);
    }

    function executeClaim(bytes32 nodeID) external {
        sm.executeClaim(nodeID);
    }

    function setMinStake(uint256 newMinStake) external {
        sm.setMinStake(newMinStake);
    }

    function govWithdraw() external {
        sm.govWithdraw();
    }

    function govWithdrawEth() external {
        sm.govWithdrawEth();
    }

    // Vault

    function allBatch(
        SigData calldata sigData,
        bytes32[] calldata fetchSwapIDs,
        IERC20[] calldata fetchTokens,
        IERC20[] calldata tranTokens,
        address payable[] calldata tranRecipients,
        uint256[] calldata tranAmounts
    ) external {
        v.allBatch(sigData, fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts);
    }

    function transfer(
        SigData calldata sigData,
        IERC20 token,
        address payable recipient,
        uint256 amount
    ) external {
        v.transfer(sigData, token, recipient, amount);
    }

    function transferBatch(
        SigData calldata sigData,
        IERC20[] calldata tokens,
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        v.transferBatch(sigData, tokens, recipients, amounts);
    }

    function fetchDepositEth(SigData calldata sigData, bytes32 swapID) external {
        v.fetchDepositEth(sigData, swapID);
    }

    function fetchDepositEthBatch(SigData calldata sigData, bytes32[] calldata swapIDs) external {
        v.fetchDepositEthBatch(sigData, swapIDs);
    }

    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        IERC20 token
    ) external {
        v.fetchDepositToken(sigData, swapID, token);
    }

    function fetchDepositTokenBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        IERC20[] calldata tokens
    ) external {
        v.fetchDepositTokenBatch(sigData, swapIDs, tokens);
    }

    function swapETH(string calldata egressParams, bytes32 egressReceiver) external {
        v.swapETH(egressParams, egressReceiver);
    }

    function swapToken(
        string calldata egressParams,
        bytes32 egressReceiver,
        address ingressToken,
        uint256 amount
    ) external {
        v.swapToken(egressParams, egressReceiver, ingressToken, amount);
    }

    function govWithdraw(IERC20[] calldata tokens) external {
        v.govWithdraw(tokens);
    }

    function enableSwaps() external {
        v.enableSwaps();
    }

    function disableSwaps() external {
        v.disableSwaps();
    }

    // FLIP

    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber,
        address staker
    ) external {
        f.updateFlipSupply(sigData, newTotalSupply, stateChainBlockNumber, staker);
    }


    // Property testing

    // Just for testing purposes
    function echidna_pass() external pure returns (bool) {
        return true;
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

    // No function call that requires signing should pass the signature check
    function echidna_lastValidateTime() external returns (bool) {
        return _lastValidateTime == km.getLastValidateTime();
    }
}
