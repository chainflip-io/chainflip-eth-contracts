pragma solidity ^0.8.0;

import "../contracts/helpers.sol";
import "./NewTestReceiver.sol";
import "./MockToken.sol";
import "../../deployers/DeployerContract.sol";
import "../../Vault.sol";
import "../../KeyManager.sol";
import "../../StateChainGateway.sol";
import "../../FLIP.sol";
import "../../interfaces/IShared.sol";

contract NewTestEchidna is IShared {
    // Events for debugging (can be replaced by crytic/properties helpers)
    event log_string(string);
    event log_uint(uint256);
    event log_addr(address);

    // Randomly obtained via privatekeys.pw, except the aggregate
    bytes32 internal govPK = 0xb670a09c7ecb70fe3d1616ea441f7f2f3d36ca2ad7281ae51d3a068910a2b7a1;
    address internal govKey = address(0x3421b011C6a5f7c1ED438368565A5A8943063D19);
    bytes32 internal commPK = 0xf8b408fd2e00c01ed0810614d34ed23d27b67952fd2f07267fbeec845ef24cc7;
    address internal commKey = address(0x6C377BdD40216c5b997Ab2bf0CFF8c2624F9Dd86);
    bytes32 internal aggPK = 0xfbcb47bc85b881e0dfb31c872d4e06848f80530ccbd18fc016a27c4a744d0eba;
    uint256 internal minStake = 1000 * E_18;

    // Common constants across tests
    uint256 internal constant E_18 = 10 ** 18;
    uint256 internal constant PUBKEYX = 22479114112312168431982914496826057754130808976066989807481484372215659188398;
    uint8 internal constant PUBKEYYPARITY = 1;
    uint256 internal constant INIT_SUPPLY = 9 * 10 ** 7 * E_18;
    uint256 internal constant NUM_GENESIS_VALIDATORS = 5;
    uint256 internal constant GENESIS_STAKE = 5000 * E_18;

    // Node ID and nonce
    uint256 internal nodeid = 1;
    uint256 internal nonce = 0;

    // State variables
    DeployerContract internal dc;
    Vault internal vault;
    KeyManager internal keyManager;
    StateChainGateway internal stateChainGateway;
    FLIP internal flip;
    NewTestReceiver internal receiver;
    MockToken[] internal tokens;
    mapping(uint256 => address) internal stakingAddresses;
    mapping(uint256 => uint256) internal redemptionedAmounts;
    mapping(uint256 => bool) internal redemptionableNodeID;

    // Echidna requires that no parameters are passed to the constructor so we need to set
    // constants for the deployments of the contracts
    constructor() {
        dc = new DeployerContract(
            Key(PUBKEYX, PUBKEYYPARITY),
            govKey,
            commKey,
            minStake,
            INIT_SUPPLY,
            NUM_GENESIS_VALIDATORS,
            GENESIS_STAKE
        );

        // Local references to contracts
        vault = dc.vault();
        keyManager = dc.keyManager();
        stateChainGateway = dc.stateChainGateway();
        flip = dc.flip();

        // Mock tokens (can be extended to any size)
        tokens.push(new MockToken("One token", "OTK"));
        tokens.push(new MockToken("Yet another token", "YAT"));

        // Receiver contract to test vault calls
        hevm.prank(govKey);
        receiver = new NewTestReceiver(address(vault), address(stateChainGateway), address(flip));
    }

    // ===============================================================================================
    //                                       Helpers
    // ===============================================================================================

    function generate_new_aggregate_key() internal returns (Key memory k, bytes32 priv_key) {
        string[] memory inp = new string[](2);
        inp[0] = "python3";
        inp[1] = "tests/keygen.py";

        bytes memory res = hevm.ffi(inp);
        (uint256 priv, uint256 pubKeyX, uint8 pubKeyYParity) = abi.decode(res, (uint256, uint256, uint8));
        k.pubKeyX = pubKeyX;
        k.pubKeyYParity = pubKeyYParity;
        priv_key = bytes32(priv);
    }

    function generate_new_keymanager() internal returns (KeyManager km, bytes32 priv_key) {
        Key memory newagg;

        (newagg, priv_key) = generate_new_aggregate_key();

        km = new KeyManager(newagg, govKey, commKey);
    }

    function sign_message_with_key(
        bytes32 message,
        uint256 sigNonce,
        bytes32 key,
        address sender,
        address cont
    ) internal returns (SigData memory out) {
        out.nonce = sigNonce;

        bytes32 msgHash = keccak256(abi.encode(message, sigNonce, sender, block.chainid, cont));

        string[] memory inp = new string[](5);
        inp[0] = "python3";
        inp[1] = "tests/signer.py";
        inp[2] = bytesToString(bytes.concat(msgHash));
        inp[3] = bytesToString(bytes.concat(key));
        inp[4] = toString(sigNonce);

        bytes memory res = hevm.ffi(inp);
        (uint256 signed, address ktimesg) = abi.decode(res, (uint256, address));

        out.sig = signed;
        out.kTimesGAddress = ktimesg;
    }

    function test_get_tokens_from_gov(uint256 amount) public {
        hevm.prank(govKey);
        flip.transfer(msg.sender, amount);

        hevm.prank(msg.sender);
        flip.approve(address(stateChainGateway), type(uint256).max);

        hevm.prank(msg.sender);
        flip.approve(address(vault), type(uint256).max);
    }

    // ===============================================================================================
    //                    Wrappers for functions needing signatures in KeyManager
    // ===============================================================================================

    // The sender field for signatures here is always address(keyManager)
    function test_set_agg_key_with_agg_key(Key calldata newkey) public {
        bytes32 message = keccak256(abi.encode(keyManager.setAggKeyWithAggKey.selector, newkey));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(keyManager), address(keyManager));
        nonce++;

        keyManager.setAggKeyWithAggKey(sig, newkey);

        assert(keccak256(abi.encode(newkey)) == keccak256(abi.encode(keyManager.getAggregateKey())));
    }

    function test_set_gov_key_with_agg_key(address newkey) public {
        bytes32 message = keccak256(abi.encode(keyManager.setGovKeyWithAggKey.selector, newkey));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(keyManager), address(keyManager));
        nonce++;

        keyManager.setGovKeyWithAggKey(sig, newkey);

        assert(newkey == keyManager.getGovernanceKey());
    }

    function test_set_comm_key_with_agg_key(address newkey) public {
        bytes32 message = keccak256(abi.encode(keyManager.setCommKeyWithAggKey.selector, newkey));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(keyManager), address(keyManager));
        nonce++;

        keyManager.setCommKeyWithAggKey(sig, newkey);

        assert(newkey == keyManager.getCommunityKey());
    }

    // ===============================================================================================
    //                 Wrappers for functions needing signatures in StateChainGateway
    // ===============================================================================================

    // this will need some sanity check on the values (can we interact with the sc from echidna?)
    function test_update_flip_supply(uint256 new_supply, uint256 sc_blocknumber) public {
        bytes32 message = keccak256(
            abi.encode(stateChainGateway.updateFlipSupply.selector, new_supply, sc_blocknumber)
        );

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        uint256 flip_supply = flip.totalSupply();
        uint256 prev_balance = flip.balanceOf(address(stateChainGateway));
        bool increased = new_supply > flip_supply;

        stateChainGateway.updateFlipSupply(sig, new_supply, sc_blocknumber);

        if (increased) {
            uint256 difference = new_supply - flip_supply;
            assert(flip.balanceOf(address(stateChainGateway)) == prev_balance + difference);
        } else {
            uint256 difference = flip_supply - new_supply;
            assert(flip.balanceOf(address(stateChainGateway)) == prev_balance - difference);
        }
    }

    // does not check that the argument is indeed a key manager
    function test_update_stateChainGateway_key_manager(address newkeyman) internal {
        bytes32 message = keccak256(abi.encode(stateChainGateway.updateKeyManager.selector, newkeyman));

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        stateChainGateway.updateKeyManager(sig, IKeyManager(newkeyman), false);

        assert(newkeyman == address(stateChainGateway.getKeyManager()));
    }

    // Token staking test
    function test_fund(uint256 amount) public {
        hevm.prank(msg.sender);
        stateChainGateway.fundStateChainAccount(bytes32(nodeid), amount);
        stakingAddresses[nodeid] = msg.sender;
        redemptionableNodeID[nodeid] = true;

        nodeid++;
    }

    // funder will be msg.sender for now
    function test_register_redemption(uint256 node, uint256 amount, uint48 expiryTime) public {
        uint256 nodeID = 1 + (node % (nodeid - 1));
        address funder = msg.sender;

        require(redemptionableNodeID[nodeID] == true);

        bytes32 message = keccak256(
            abi.encode(stateChainGateway.registerRedemption.selector, nodeID, amount, funder, expiryTime)
        );

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        stateChainGateway.registerRedemption(sig, bytes32(nodeID), amount, funder, expiryTime);
        StateChainGateway.Redemption memory result = stateChainGateway.getPendingRedemption(bytes32(nodeID));

        redemptionedAmounts[nodeID] = amount;

        assert(result.redeemAddress == stakingAddresses[nodeID]);
    }

    function test_execute_redemption(uint256 node) public {
        uint256 nodeID = 1 + (node % (nodeid - 1));
        uint256 balance_before = flip.balanceOf(stakingAddresses[nodeID]);

        // Execute the redemption
        stateChainGateway.executeRedemption(bytes32(nodeID));

        // Make sure the redemption was fulfilled
        assert(flip.balanceOf(stakingAddresses[nodeID]) == balance_before + redemptionedAmounts[nodeID]);

        redemptionableNodeID[nodeID] = false;
    }

    function test_update_flip_issuer(address new_issuer) public {
        require(new_issuer != address(0));
        bytes32 message = keccak256(abi.encode(stateChainGateway.updateFlipIssuer.selector, new_issuer));

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        stateChainGateway.updateFlipIssuer(sig, new_issuer, false);

        assert(flip.getIssuer() == new_issuer);
    }

    // ===============================================================================================
    //                 Wrappers for functions needing signatures in Vault
    // ===============================================================================================

    // does not check that the argument is indeed a key manager
    function test_update_vault_key_manager(address newkeyman) internal {
        bytes32 message = keccak256(abi.encode(vault.updateKeyManager.selector, newkeyman));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.updateKeyManager(sig, IKeyManager(newkeyman), false);

        assert(newkeyman == address(vault.getKeyManager()));
    }

    // this doesn't perform any check after executing, can be used to test reentrancy
    function test_execute_xswap_and_call(
        uint8 token,
        uint256 amount,
        uint32 src_chain,
        bytes calldata src_addr,
        bytes calldata mess
    ) public {
        MockToken token_addr = tokens[token % tokens.length];

        TransferParams memory t_params;
        t_params.token = address(token_addr);
        t_params.recipient = payable(address(receiver));
        t_params.amount = amount;

        hevm.prank(address(this));
        token_addr.mint(address(vault), amount);

        bytes32 message = keccak256(
            abi.encode(vault.executexSwapAndCall.selector, t_params, src_chain, src_addr, mess)
        );

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.executexSwapAndCall(sig, t_params, src_chain, src_addr, mess);
    }

    function test_execute_xcall(uint32 srcChain, bytes calldata srcAddress, bytes calldata mess) public {
        address recipient = address(receiver);

        bytes32 message = keccak256(abi.encode(vault.executexCall.selector, recipient, srcChain, srcAddress, mess));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.executexCall(sig, recipient, srcChain, srcAddress, mess);
    }

    function test_execute_actions(uint8 token, uint256 amount, IMulticall.Call[] calldata calls) public {
        MockToken token_addr = tokens[token % tokens.length];
        address multicall_addr = address(receiver);

        // TODO: Add gas amount to the fuzzing
        uint256 gasMulticall = 100000;

        hevm.prank(address(this));
        token_addr.mint(address(vault), amount);

        TransferParams memory t_params = TransferParams(address(token_addr), payable(multicall_addr), amount);

        bytes32 message = keccak256(abi.encode(vault.executeActions.selector, t_params, calls, gasMulticall));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.executeActions(sig, t_params, calls, gasMulticall);
    }

    function test_vault_transfer(TransferParams calldata t_params) public {
        bytes32 message = keccak256(abi.encode(vault.transfer.selector, t_params));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.transfer(sig, t_params);
    }

    function test_vault_transfer_batch(TransferParams[] calldata t_params) public {
        bytes32 message = keccak256(abi.encode(vault.transferBatch.selector, t_params));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.transferBatch(sig, t_params);
    }

    // ===============================================================================================
    //           Wrappers for simplifying testing of transactions needing specific values
    // ===============================================================================================

    function test_create_new_keymanager_and_update_all() public {
        (KeyManager km, bytes32 pk) = generate_new_keymanager();

        test_update_vault_key_manager(address(km));
        test_update_stateChainGateway_key_manager(address(km));

        aggPK = pk;
        keyManager = km;
    }

    function test_fund_plus_redemption(uint256 amount) public {
        // Get a valid random amount between 10**19 and 10**19 + 10**30 - 1
        uint256 to_fund = 10 ** 19 + (amount % 10 ** 30);

        // Get tokens from governance
        hevm.prank(govKey);
        flip.transfer(msg.sender, amount);

        hevm.prank(msg.sender);
        flip.approve(address(stateChainGateway), type(uint256).max);

        hevm.prank(msg.sender);
        flip.approve(address(vault), type(uint256).max);

        hevm.prank(msg.sender);
        test_fund(to_fund);

        hevm.prank(govKey);
        test_register_redemption(nodeid - 1, to_fund, uint48(block.timestamp + 3 days));

        hevm.warp(block.timestamp + 2 days + 500);

        hevm.prank(msg.sender);
        test_execute_redemption(nodeid - 1);
    }

    function test_stateChainGateway_gov_withdrawal() public {
        hevm.prank(commKey);
        stateChainGateway.disableCommunityGuard();

        hevm.prank(govKey);
        stateChainGateway.suspend();

        hevm.prank(govKey);
        stateChainGateway.govWithdraw();
    }

    function test_vault_gov_withdrawal() public {
        address[] memory token_list = new address[](tokens.length);

        for (uint256 i = 0; i < tokens.length; i++) {
            token_list[i] = address(tokens[i]);
        }

        hevm.prank(commKey);
        stateChainGateway.disableCommunityGuard();

        hevm.prank(govKey);
        stateChainGateway.suspend();

        hevm.warp(block.timestamp + 14 days + 1);

        hevm.prank(govKey);
        vault.govWithdraw(token_list);
    }

    // ===============================================================================================
    //                                    Invariants
    // ===============================================================================================

    // Flip address in StateChainGateway must not change
    function test_constant_flip() external {
        assert(address(stateChainGateway.getFLIP()) == address(flip));
    }

    // All keymanager references must be the same
    function test_keymanager_consistency() external {
        assert(stateChainGateway.getKeyManager() == vault.getKeyManager());
    }

    // All govKey references must be the same
    function test_govkey_consistency() external {
        assert(stateChainGateway.getGovernor() == vault.getGovernor());
        assert(vault.getGovernor() == keyManager.getGovernanceKey());
    }

    // All commKey references must be the same
    function test_commkey_consistency() external {
        assert(stateChainGateway.getCommunityKey() == vault.getCommunityKey());
        assert(vault.getCommunityKey() == keyManager.getCommunityKey());
    }
}
