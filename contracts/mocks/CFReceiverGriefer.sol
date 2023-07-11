pragma solidity ^0.8.0;

import "./CFReceiverMock.sol";

/**
 * @title    CFReceiverGriefer
 * @dev      Mock implementation of CFReceiver to test CCM gas attacks.
 */

contract CFReceiverGriefer is CFReceiverMock {
    uint256[] public iterations;
    uint256 public numiterations = 400;

    constructor(address _cfVault) CFReceiverMock(_cfVault) {}

    // This will consume ~9M gas
    function _cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        super._cfReceive(srcChain, srcAddress, message, token, amount);
        for (uint256 i = 0; i < numiterations; i++) {
            iterations.push(i);
        }
    }

    function _cfReceivexCall(uint32 srcChain, bytes calldata srcAddress, bytes calldata message) internal override {
        super._cfReceivexCall(srcChain, srcAddress, message);
    }
}
