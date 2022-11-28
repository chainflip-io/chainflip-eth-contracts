pragma solidity ^0.8.0;

import "../abstract/CFReceiver.sol";
import "../abstract/Shared.sol";
import "../interfaces/IVault.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title    DexAggMock
 * @dev      Mock implementation of a DEX Aggregator for testing purposes. This
 *           contract will have both the ingress and egress calls from Chainflip's
 *           point of view. A swap before CF swap is not mimicked here as that is
 *           part of the DEX Aggregator's responsibility. Only the xSwapAndCall is
 *           to be tested - xSwap plus xCall with decoding of the data.
 *           This is a Mock, not a real contract. DO NOT USE in production.
 */

contract DexAggMock is CFReceiver, Shared {
    using SafeERC20 for IERC20;

    event ReceivedxSwapAndCall(
        uint32 srcChain,
        string srcAddress,
        bytes message,
        address token,
        uint256 amount,
        uint256 ethReceived
    );
    event ReceivedxCall(uint32 srcChain, string srcAddress, bytes message, uint256 ethReceived);

    constructor(address cfSender) CFReceiver(cfSender) nzAddr(cfSender) {}

    function xSwapNativeAndCall(
        uint32 dstChain,
        string calldata dstAddress,
        string calldata swapIntent,
        address refundAddress,
        address dstToken,
        address userToken,
        address userAddress
    ) external {
        // NOTE: LiFi contracts as of now do the message encoding on-chain, which seems
        // like a waste of gas to me. Interestinngly, they also do encodePacked which might
        // be a good idea if there is only one dynamic type. However, it seems like it's the only
        // bridge where they do that, so it is probably not their final solution.
        // NOTE: We skip all the checks. This is not a real contract, just a mock.

        // Encoding of data should probably be done off-chain to save gas. This is just for
        // making the testing easier and to show what we are actually doing.
        // Encoding several parameters to proof that parameters beyond the function call
        // can be encoded.
        bytes4 FUNC_SELECTOR = bytes4(keccak256("swapMock(address, uint256,uint256)"));
        //bytes memory calldataDstxCall=abi.encode(FUNC_SELECTOR,dstToken,userToken,userAddress);

        // We could use encodePacked, but it's not a good idea if there are multiple dynamic types,
        // like if the dstChain was non-EVM and then the userAddress would need to be a string.
        // For dstAddress, we pass it directly as a string, but it could also be done on-chain
        // with OZ's `strings.toHexString(params.destinationAddress)`;
        bytes memory message = abi.encode(FUNC_SELECTOR, dstToken, userToken, userAddress);

        // Hardcoding the swapAmount just to ease the testing.
        //bytes memory calldataDstxCall = abi.encodeWithSignature("swap(address,address,uint256)", dstToken, userToken, 100);

        IVault(_cfSender).xSwapNativeAndCall(dstChain, dstAddress, swapIntent, message, refundAddress);
    }

    function _cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        require(token != _ETH_ADDR, "DexAggMock: Only tokens are supported in testing");

        (bytes4 selector, address dstToken, address userToken, address userAddress) = abi.decode(
            message,
            (bytes4, address, address, address)
        );

        // Instead of the calldata being a call to a DEX we just do an mock call
        (bool success, bytes memory lowLevelData) = userAddress.call(abi.encodePacked(selector, dstToken, amount));
        //(bool success, bytes memory lowLevelData) = userAddress.call(data);
        if (!success) revert("DexAggMock: Call failed");

        // Transfer tokens to user
        IERC20(userToken).safeTransfer(userAddress, IERC20(dstToken).balanceOf(address(this)));
    }

    function _cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal override {
        emit ReceivedxCall(srcChain, srcAddress, message, msg.value);
    }
}

contract DEX {
    using SafeERC20 for IERC20;

    function swapMock(
        address tokenIn,
        address tokenOut,
        uint256 amount
    ) external {
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amount);

        // Mocking the swap with a 1:2 ratio.
        IERC20(tokenOut).safeTransfer(msg.sender, amount * 2);
    }
}
