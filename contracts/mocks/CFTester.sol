// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./CFReceiverMock.sol";
import "../interfaces/IVault.sol";

/**
 * @title    CFTester
 * @dev      Contract used for testing Chainflip behaviour.
 */

contract CFTester is CFReceiverMock {
    using SafeERC20 for IERC20;

    uint256[] public iterations;
    uint256 public gasIterations = 300;

    bytes public constant GAS_MESSAGE = abi.encode("GasTest");

    constructor(address _cfVault) CFReceiverMock(_cfVault) {}

    function _cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        super._cfReceive(srcChain, srcAddress, message, token, amount);
        if (keccak256(message) == keccak256(GAS_MESSAGE)) {
            _consumeGas();
        }
    }

    function _cfReceivexCall(uint32 srcChain, bytes calldata srcAddress, bytes calldata message) internal override {
        super._cfReceivexCall(srcChain, srcAddress, message);
        if (keccak256(message) == keccak256(GAS_MESSAGE)) {
            _consumeGas();
        }
    }

    // This will consume ~6.5M gas
    function _consumeGas() internal {
        for (uint256 i = 0; i < gasIterations; i++) {
            iterations.push(i);
        }
    }

    function transferEth(address payable to) external payable {
        (bool success, ) = to.call{value: msg.value}("");
        require(success, "Transfer failed.");
    }

    function transferToken(address to, IERC20 srcToken, uint256 amount) external payable {
        srcToken.safeTransferFrom(msg.sender, address(this), amount);
        srcToken.transfer(to, amount);
    }

    function multipleContractSwap(
        uint32 dstChain,
        bytes memory dstAddress,
        uint32 dstToken,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters,
        uint8 numSwaps
    ) external payable {
        if (srcToken == IERC20(_NATIVE_ADDR)) {
            require(msg.value == amount * numSwaps, "CFTester: Amount doesn't match value");
            for (uint i = 0; i < numSwaps; i++) {
                IVault(cfVault).xSwapNative{value: amount}(dstChain, dstAddress, dstToken, cfParameters);
            }
        } else {
            srcToken.safeTransferFrom(msg.sender, address(this), amount * numSwaps);
            require(IERC20(srcToken).approve(cfVault, amount * numSwaps));
            for (uint i = 0; i < numSwaps; i++) {
                IVault(cfVault).xSwapToken(dstChain, dstAddress, dstToken, srcToken, amount, cfParameters);
            }
        }
    }

    function multipleContractCall(
        uint32 dstChain,
        bytes memory dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 gasAmount,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters,
        uint8 numSwaps
    ) external payable {
        if (srcToken == IERC20(_NATIVE_ADDR)) {
            require(msg.value == amount * numSwaps, "CFTester: Amount doesn't match value");
            for (uint i = 0; i < numSwaps; i++) {
                IVault(cfVault).xCallNative{value: amount}(
                    dstChain,
                    dstAddress,
                    dstToken,
                    message,
                    gasAmount,
                    cfParameters
                );
            }
        } else {
            srcToken.safeTransferFrom(msg.sender, address(this), amount * numSwaps);
            require(IERC20(srcToken).approve(cfVault, amount * numSwaps));
            for (uint i = 0; i < numSwaps; i++) {
                IVault(cfVault).xCallToken(
                    dstChain,
                    dstAddress,
                    dstToken,
                    message,
                    gasAmount,
                    srcToken,
                    amount,
                    cfParameters
                );
            }
        }
    }
}
