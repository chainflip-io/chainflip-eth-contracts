// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract TetherTokenTester {
    using SafeERC20 for IERC20;

    event DebugEvent(
        address indexed recipient,
        uint256 amount,
        address indexed tokenAddr,
        bytes reason,
        bool transferred
    );

    function lowLevelTransfer(address token) public {
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, bytes memory returndata) = address(token).call(
            abi.encodeWithSelector(IERC20.transfer.selector, msg.sender, 1)
        );
        require(success, "Failed");
        emit DebugEvent(msg.sender, 1, address(token), returndata, success);
    }

    function lowLevelTransferLegacy(address token) public {
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, bytes memory returndata) = token.call(
            abi.encodeWithSelector(IERC20(token).transfer.selector, msg.sender, 1)
        );

        // No need to check token.code.length since it comes from a gated call
        bool transferred = success && (returndata.length == uint256(0) || abi.decode(returndata, (bool)));
        if (!transferred) emit DebugEvent(msg.sender, 1, token, returndata, success);
    }

    function safeTransfer(address token) public {
        IERC20(token).safeTransfer(msg.sender, 1);
    }

    function regularTransfer(address token) public {
        bool success = IERC20(token).transfer(msg.sender, 1);
        emit DebugEvent(msg.sender, 1, address(token), "", success);
    }

    function regularTransferRequire(address token) public {
        require(IERC20(token).transfer(msg.sender, 1), "fail");
    }
}
