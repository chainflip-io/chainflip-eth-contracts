pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../abstract/CFReceiver.sol";
import "../abstract/Shared.sol";
import "../interfaces/IVault.sol";

bytes4 constant FUNC_SELECTOR = bytes4(keccak256("swapMock(address,address,uint256)"));

/**
 * @dev      Mock implementation of a DEX Aggregator for testing purposes. There are three
 *           mocks in this file: the DEX Aggregator contract on the source chain, the one on
 *           the destination chain, and the mock DEX contract called on the destination chain.
 *           The flow is as follows:
 *           Native:Chain1 (User to Vault) -> Token:Chain2 (CF swap) -> Token2:Chain2 (DexMock swap)
 *           The DexMockSwap parameters are encoded on the srcChain as part of the message and decoded
 *           on the dstChain.
 *           This contract is a Mock and this is not the actual implementation of a DEX Aggregator.
 *           The contract is only for testing purposes to do a proof of concept of a full cross-chain
 *           swap with a DEX Aggregator, do not inherit nor use in production.
 */

contract DexAggSrcChainMock is Shared {
    using SafeERC20 for IERC20;

    address private _cfVault;

    constructor(address cfVault) nzAddr(cfVault) {
        _cfVault = cfVault;
    }

    // Ingress Chain
    function swapNativeAndCallViaChainflip(
        uint32 dstChain,
        string calldata dstAddress,
        string calldata swapIntent,
        address dexAddress,
        address dstToken,
        address userToken,
        address userAddress
    ) external payable {
        // Encoding of data should probably be done off-chain to save gas. This is just for making the
        // testing easier. Any parameter can be encoded in the message. Here we encode the function
        // selector along with other parameters that will be used in the destination chain's contract
        // in order to make the call to the DEXMock.
        bytes memory message = abi.encode(FUNC_SELECTOR, dexAddress, dstToken, userToken, userAddress);
        IVault(_cfVault).xSwapNativeAndCall{value: msg.value}(dstChain, dstAddress, swapIntent, message, msg.sender);
    }

    function swapTokenAndCallViaChainflip(
        uint32 dstChain,
        string calldata dstAddress,
        string calldata swapIntent,
        address dexAddress,
        address dstToken,
        address userToken,
        address userAddress,
        address srcToken,
        uint256 srcAmount
    ) external {
        IERC20(srcToken).safeTransferFrom(msg.sender, address(this), srcAmount);

        // Encoding of data should probably be done off-chain to save gas. This is just for making the
        // testing easier. Any parameter can be encoded in the message. Here we encode the function
        // selector along with other parameters that will be used in the destination chain's contract
        // in order to make the call to the DEXMock.
        bytes memory message = abi.encode(FUNC_SELECTOR, dexAddress, dstToken, userToken, userAddress);
        IERC20(srcToken).approve(_cfVault, srcAmount);
        IVault(_cfVault).xSwapTokenAndCall(
            dstChain,
            dstAddress,
            swapIntent,
            message,
            IERC20(srcToken),
            srcAmount,
            msg.sender
        );
    }
}

contract DexAggDstChainMock is CFReceiver, Shared {
    using SafeERC20 for IERC20;

    // @dev Mapping of chain to DexAggSrcChainMock's source Chain's address. Storing it
    // without the initial "0x" just because brownie has issues passing a string with
    // the same length as an address (it mistakenly thinks it's an address).
    mapping(uint256 => string) private _chainToAddress;

    event ReceivedxSwapAndCall(
        uint32 srcChain,
        string srcAddress,
        bytes message,
        address token,
        uint256 amount,
        uint256 ethReceived
    );
    event ReceivedxCall(uint32 srcChain, string srcAddress, bytes message, uint256 ethReceived);

    constructor(
        address cfSender,
        uint256 srcChain,
        string memory srcChainAddress
    ) CFReceiver(cfSender) nzAddr(cfSender) {
        _chainToAddress[srcChain] = srcChainAddress;
    }

    // Egress Chain
    function _cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        require(
            keccak256(abi.encodePacked(_chainToAddress[srcChain])) == keccak256(abi.encodePacked(srcAddress)),
            "DexAggMock: Invalid source chain address"
        );

        (bytes4 selector, address dexAddress, address dstToken, address userToken, address userAddress) = abi.decode(
            message,
            (bytes4, address, address, address, address)
        );

        require(dstToken == token, "DexAggMock: Assertion failed");

        if (token != _ETH_ADDR) {
            IERC20(dstToken).approve(dexAddress, amount);
        }

        // Check that the srcChain's encoded selector matches what we are decoding on the dstChain.
        require(selector == FUNC_SELECTOR, "DexAggMock: Invalid selector");

        uint256 msgValue = token == _ETH_ADDR ? amount : 0;
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = dexAddress.call{value: msgValue}(
            abi.encodeWithSelector(selector, dstToken, userToken, amount)
        );
        if (!success) revert("DexAggMock: Call failed");

        // Transfer tokens to user
        IERC20(userToken).safeTransfer(userAddress, IERC20(userToken).balanceOf(address(this)));
    }

    function _cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal override {
        emit ReceivedxCall(srcChain, srcAddress, message, msg.value);
    }

    receive() external payable {}
}

contract DEXMock is Shared {
    using SafeERC20 for IERC20;

    function swapMock(
        address tokenIn,
        address tokenOut,
        uint256 amount
    ) external payable {
        if (tokenIn == _ETH_ADDR) {
            require(msg.value == amount, "DEXMock: Invalid amount");
        } else {
            IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amount);
        }

        // Mocking the swap with a 1:2 ratio.
        if (tokenOut == _ETH_ADDR) {
            payable(msg.sender).transfer(amount * 2);
        } else {
            IERC20(tokenOut).safeTransfer(msg.sender, amount * 2);
        }
    }
}