pragma solidity ^0.8.0;

import "../abstract/CFReceiver.sol";
import "../abstract/Shared.sol";

/**
 * @title    CFReceiverMock
 * @dev      Mock implementation of CFReceiver for testing purposes.
 */

contract CFReceiverMock is CFReceiver, Shared {
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

    function _cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        emit ReceivedxSwapAndCall(srcChain, srcAddress, message, token, amount, msg.value);
    }

    function _cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal override {
        emit ReceivedxCall(srcChain, srcAddress, message, msg.value);
    }
}
