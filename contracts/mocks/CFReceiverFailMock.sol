pragma solidity ^0.8.0;

import "../abstract/CFReceiver.sol";
import "../abstract/Shared.sol";

/**
 * @title    CFReceiverMock
 * @dev      Mock implementation of CFReceiver for testing purposes.
 */

contract CFReceiverFailMock is CFReceiver, Shared {
    constructor(address cfSender) CFReceiver(cfSender) nzAddr(cfSender) {}

    function _cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        _revert();
    }

    function _cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal override {
        _revert();
    }

    function revertExternalCall() external {
        _revert();
    }

    function _revert() internal {
        revert("CFReceiverFail: call reverted");
    }
}
