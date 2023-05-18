pragma solidity ^0.8.0;

import "../../deployers/DeployerContract.sol";
import "../../Vault.sol";
import "../../KeyManager.sol";
import "../../StateChainGateway.sol";
import "../../FLIP.sol";
import "../../abstract/CFReceiver.sol";
import "../../interfaces/IShared.sol";

contract NewTestReceiver is CFReceiver, IMulticall {
    address vault;
    address flip;
    address fund_manager;

    address[] public callTargets;
    bytes[] public callArguments;

    constructor(address _vault, address _fund_manager, address _flip) CFReceiver(_vault) {
        vault = _vault;
        fund_manager = _fund_manager;
        flip = _flip;
    }

    function _process_call_sequence() internal {
        for (uint256 i = 0; i < callTargets.length; i++) {
            callTargets[i].call(callArguments[i]);
        }
    }

    // IMulticall override
    function run(Call[] calldata calls, address token, uint256 amount) external payable {
        _process_call_sequence();
    }

    // CFReceiver overrides
    function _cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        // Ignore all parameters, this will only call the function stack in order
        _process_call_sequence();
    }

    function _cfReceivexCall(uint32 srcChain, bytes calldata srcAddress, bytes calldata message) internal override {
        // Ignore all parameters, this will only call the function stack in order
        _process_call_sequence();
    }

    // We should add here all the unprivileged functions that can be called

    function add_flip_approve(address spender, uint256 amount) public {
        callTargets.push(flip);
        callArguments.push(abi.encodeWithSelector(ERC20.approve.selector, spender, amount));
    }

    function add_flip_transfer(address to, uint256 amount) public {
        callTargets.push(flip);
        callArguments.push(abi.encodeWithSelector(ERC20.transfer.selector, to, amount));
    }

    function add_fund_manager_fund(bytes32 id, uint256 amount, address return_addr) public {
        callTargets.push(fund_manager);
        callArguments.push(
            abi.encodeWithSelector(StateChainGateway.fundStateChainAccount.selector, id, amount, return_addr)
        );
    }

    function add_fund_manager_execute(bytes32 id) public {
        callTargets.push(fund_manager);
        callArguments.push(abi.encodeWithSelector(StateChainGateway.executeRedemption.selector, id));
    }

    function add_vault_xswaptoken(
        uint32 dstchain,
        bytes memory dstaddr,
        uint16 dsttoken,
        address srctoken,
        uint256 amount
    ) public {
        callTargets.push(vault);
        callArguments.push(
            abi.encodeWithSelector(Vault.xSwapToken.selector, dstchain, dstaddr, dsttoken, IERC20(srctoken), amount)
        );
    }
}
