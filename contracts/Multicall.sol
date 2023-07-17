// SPDX-License-Identifier: MIT

pragma solidity ^0.8.17;

import {IERC20} from "../node_modules/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IERC721Receiver} from "../node_modules/@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {IERC1155Receiver} from "../node_modules/@openzeppelin/contracts/token/ERC1155/IERC1155Receiver.sol";

import "./interfaces/IMulticall.sol";
import "./abstract/Shared.sol";

/**
 * @title    Multicall
 * @dev      This contract is called by the Chainflip Vault to execute actions on behalf of the
 *           the Vault but in a separate contract to minimize risks.
 *           This contract is immutable and if the Chainflip Vault is upgraded to a new contract
 *           this contract will also need to be redeployed. This is to prevent any changes of
 *           behaviour in this contract while the Vault is making calls to it.
 *           This contract is based on the SquidMulticall contract from the SquidRouter protocol
 *           with an added layer of access control. There is also an extra _safeTransferFrom()
 *           since this contract will get the tokens approved by the Vault instead of transferred.
 */
contract Multicall is IMulticall, IERC721Receiver, IERC1155Receiver, Shared {
    bytes4 public constant ERC165_INTERFACE_ID = 0x01ffc9a7;
    bytes4 public constant ERC721_TOKENRECEIVER_INTERFACE_ID = 0x150b7a02;
    bytes4 public constant ERC1155_TOKENRECEIVER_INTERFACE_ID = 0x4e2312e0;

    bool private isRunning;
    /// @dev    Chainflip's Vault address
    address public immutable cfVault;

    error TransferFailed();

    constructor(address _cfVault) nzAddr(_cfVault) {
        cfVault = _cfVault;
    }

    function run(Call[] calldata calls, address tokenIn, uint256 amountIn) external payable override onlyCfVault {
        // Prevents reentrancy
        if (isRunning) revert AlreadyRunning();
        isRunning = true;

        if (amountIn > 0 && tokenIn != _NATIVE_ADDR) {
            _safeTransferFrom(tokenIn, msg.sender, amountIn);
        }

        for (uint256 i = 0; i < calls.length; i++) {
            Call memory call = calls[i];

            if (call.callType == CallType.FullTokenBalance) {
                (address token, uint256 amountParameterPosition) = abi.decode(call.payload, (address, uint256));
                uint256 amount = IERC20(token).balanceOf(address(this));
                _setCallDataParameter(call.callData, amountParameterPosition, amount);
            } else if (call.callType == CallType.FullNativeBalance) {
                call.value = address(this).balance;
            } else if (call.callType == CallType.CollectTokenBalance) {
                address token = abi.decode(call.payload, (address));
                _safeTransferFrom(token, msg.sender, IERC20(token).balanceOf(msg.sender));
                continue;
            }

            // solhint-disable-next-line avoid-low-level-calls
            (bool success, bytes memory data) = call.target.call{value: call.value}(call.callData);
            if (!success) revert CallFailed(i, data);
        }

        isRunning = false;
    }

    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return
            interfaceId == ERC1155_TOKENRECEIVER_INTERFACE_ID ||
            interfaceId == ERC721_TOKENRECEIVER_INTERFACE_ID ||
            interfaceId == ERC165_INTERFACE_ID;
    }

    function _safeTransferFrom(address token, address from, uint256 amount) private {
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, bytes memory returnData) = token.call(
            abi.encodeWithSelector(IERC20.transferFrom.selector, from, address(this), amount)
        );
        bool transferred = success && (returnData.length == uint256(0) || abi.decode(returnData, (bool)));
        if (!transferred || token.code.length == 0) revert TransferFailed();
    }

    function _setCallDataParameter(bytes memory callData, uint256 parameterPosition, uint256 value) private pure {
        // solhint-disable-next-line no-inline-assembly
        assembly {
            // 36 bytes shift because 32 for prefix + 4 for selector
            mstore(add(callData, add(36, mul(parameterPosition, 32))), value)
        }
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    function onERC1155Received(address, address, uint256, uint256, bytes calldata) external pure returns (bytes4) {
        return IERC1155Receiver.onERC1155Received.selector;
    }

    function onERC1155BatchReceived(
        address,
        address,
        uint256[] calldata,
        uint256[] calldata,
        bytes calldata
    ) external pure returns (bytes4) {
        return IERC1155Receiver.onERC1155BatchReceived.selector;
    }

    // Required to enable ETH reception with .transfer or .send
    receive() external payable {}

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev Check that the sender is the Chainflip's Vault.
    modifier onlyCfVault() {
        require(msg.sender == cfVault, "Multicall: not Chainflip Vault");
        _;
    }
}
