pragma solidity ^0.8.0;

import "../abstract/CFReceiver.sol";
import "../abstract/Shared.sol";
import "../interfaces/IVault.sol";

/**
 * @title    LoopBackMock
 * @dev      Mock of a loopback.
 */
contract LoopBackMock is CFReceiver, Shared {
    constructor(address cfSender) CFReceiver(cfSender) nzAddr(cfSender) {}

    function _cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        if (token == _ETH_ADDR) {
            // Just health check for this mock. It will never revert.
            require(msg.value == amount, "LoopbackMock: msg.value != amount");
            IVault(_cfSender).xSwapNativeAndCall{value: amount}(srcChain, srcAddress, "USDC", message, address(this));
        } else {
            IERC20(token).approve(msg.sender, amount);
            IVault(_cfSender).xSwapTokenAndCall(
                srcChain,
                srcAddress,
                "USDC",
                message,
                IERC20(token),
                amount,
                address(this)
            );
        }
    }

    function _cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal override {
        IVault(_cfSender).xSwapNativeAndCall{value: 200000 * 12}(srcChain, srcAddress, "", message, address(this));
    }

    // NOTE: Comparing strings (keccak256(bytes(s1)) == keccak256(bytes(s2))) is around 1.5k gas more expensive
    // than comparing uints (this is regarding the srcChain parameter).

    // Just leaving this here as a proof of concept of slicing strings. We could make all chainNames to be
    // 3 char long so the user can know where to split the string if they need to.
    function getSlice(
        uint256 begin,
        uint256 end,
        string memory text
    ) public pure returns (string memory) {
        bytes memory a = new bytes(end - begin + 1);
        for (uint256 i = 0; i <= end - begin; i++) {
            a[i] = bytes(text)[i + begin - 1];
        }
        return string(a);
    }

    function checkChain(string memory str, string memory chainToCheck) public pure returns (bool) {
        // Additional step adding a getSlice() call if egressParams contains two parameters
        bytes memory b1 = bytes(str);
        bytes memory b2 = bytes(chainToCheck);

        require(b1.length >= b2.length, "wrong length");
        return keccak256(b1) == keccak256(b2);
    }
}
