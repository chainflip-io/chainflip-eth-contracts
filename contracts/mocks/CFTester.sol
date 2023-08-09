// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "../interfaces/IVault.sol";
import "../abstract/CFReceiver.sol";
import "../abstract/Shared.sol";

/**
 * @title    CFTester
 * @dev      Contract used for testing Chainflip behaviour.
 *           The gas calculations are not totally accurate but it's good enough for testing.
 */

contract CFTester is CFReceiver, Shared {
    using SafeERC20 for IERC20;

    uint256[] public iterations;

    // This will consume ~6.5M gas (iterations + overhead)
    uint256 public defaultNumIterations = 300;
    // This will consume ~215k
    uint256 public defaultStepIterations = 10;

    string public constant GAS_TEST = "GasTest";
    bytes public constant GAS_MESSAGE_ENCODED = bytes(GAS_TEST);

    event ReceivedxSwapAndCall(
        uint32 srcChain,
        bytes srcAddress,
        bytes message,
        address token,
        uint256 amount,
        uint256 nativeReceived,
        uint256 ccmTestGasUsed
    );
    event ReceivedxCall(uint32 srcChain, bytes srcAddress, bytes message, uint256 ccmTestGasUsed);

    constructor(address _cfVault) CFReceiver(_cfVault) nzAddr(_cfVault) {}

    function _cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        uint256 testGasUsed = _tryGasTest(message);
        emit ReceivedxSwapAndCall(srcChain, srcAddress, message, token, amount, msg.value, testGasUsed);
    }

    function _cfReceivexCall(uint32 srcChain, bytes calldata srcAddress, bytes calldata message) internal override {
        uint256 testGasUsed = _tryGasTest(message);
        emit ReceivedxCall(srcChain, srcAddress, message, testGasUsed);
    }

    function _tryGasTest(bytes calldata message) internal returns (uint256) {
        try this.decodeGasTest(message) returns (bool gasTest, uint256 gasToUse) {
            if (gasTest) {
                return _gasTest(gasToUse);
            }
        } catch {}
        return 0;
    }

    function decodeGasTest(bytes calldata message) public pure returns (bool, uint256) {
        (string memory stringMessage, uint256 gasToUse) = abi.decode(message, (string, uint256));
        return (keccak256(bytes(stringMessage)) == keccak256(GAS_MESSAGE_ENCODED), gasToUse);
    }

    // This will consume an approximate amount of gas > gasToUse
    function _gasTest(uint256 gasToUse) internal returns (uint256) {
        uint256 initialGas = gasleft();
        if (gasToUse == 0) {
            // Use default gas
            _consumeGas(defaultNumIterations);
        } else {
            while (initialGas - gasleft() < gasToUse) {
                _consumeGas(defaultStepIterations);
            }
        }
        return initialGas - gasleft();
    }

    // This consumes ~21.5k per iteration
    function _consumeGas(uint256 numIterations) internal {
        for (uint256 i = 0; i < numIterations; i++) {
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
