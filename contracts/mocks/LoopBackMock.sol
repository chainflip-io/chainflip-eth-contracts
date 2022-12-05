pragma solidity ^0.8.0;

import "../abstract/CFReceiver.sol";
import "../abstract/Shared.sol";
import "../interfaces/IVault.sol";

/**
 * @title    LoopBackMock
 * @dev      Mock of a loopback. To make it simpler we don't bother decoding the
 *           message and the callback to the Vault contract is hardcoded.
 */
contract LoopBackMock is CFReceiver, Shared {
    constructor(address cfVault) CFReceiver(cfVault) nzAddr(cfVault) {}

    function _cfReceive(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        if (token == _ETH_ADDR) {
            // Just health check for this mock. It will never revert.
            require(msg.value == amount, "LoopbackMock: msg.value != amount");
            IVault(_cfVault).xCallNative{value: amount}(srcChain, srcAddress, "USDC", message, address(this));
        } else {
            require(IERC20(token).approve(msg.sender, amount));
            IVault(_cfVault).xCallToken(srcChain, srcAddress, "USDC", message, IERC20(token), amount, address(this));
        }
    }

    function _cfReceivexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal override {
        uint256 ethBalance = address(this).balance;
        IVault(_cfVault).xCallNative{value: ethBalance}(srcChain, srcAddress, "", message, address(this));
    }

    receive() external payable {}
}
