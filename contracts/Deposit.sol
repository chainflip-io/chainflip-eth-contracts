// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./interfaces/IERC20Lite.sol";

/*****************************************************************************************************
*********************************        ATTENTION!        *******************************************
******************************************************************************************************
    Modifying this contract won't take effect on the deployed contracts as this contract's bytecode is 
    been hardcoded into the Vault contract. That is done because compiling with different environments 
    might result in different bytecodes and we need to ensure that the bytecode is consistent.
    Do NOT modify unless the consequences of doing so are fully understood. If modifications are done
    don't forget to update the Vault's DEPOSIT_BYTECODE_PRECOMPILED constant.
****************************************************************************************************/

/**
 * @title    Deposit contract
 * @notice   Creates a contract with a known address and withdraws tokens from it.
 *           After deployment, the Vault will call fetch() to withdraw tokens.
 */
contract Deposit {
    address payable private immutable vault;

    /**
     * @notice  Upon deployment it fetches the tokens (native or ERC20) to the Vault.
     * @param token  The address of the token to fetch
     */
    constructor(address token) {
        vault = payable(msg.sender);
        // Slightly cheaper to use msg.sender instead of Vault.
        if (token == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) {
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = msg.sender.call{value: address(this).balance}("");
            require(success);
        } else {
            // IERC20Lite.transfer doesn't have a return bool to avoid reverts on non-standard ERC20s
            IERC20Lite(token).transfer(msg.sender, IERC20Lite(token).balanceOf(address(this)));
        }
    }

    /**
     * @notice  Allows the Vault to fetch ERC20 tokens from this contract.
     * @param token  The address of the token to fetch
     */
    function fetch(address token) external {
        require(msg.sender == vault);
        // IERC20Lite.transfer doesn't have a return bool to avoid reverts on non-standard ERC20s
        IERC20Lite(token).transfer(msg.sender, IERC20Lite(token).balanceOf(address(this)));
    }

    /// @notice Receives native tokens, emits an event and sends them to the Vault. Note that this
    // requires the sender to forward some more gas than for a simple transfer.
    receive() external payable {
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = vault.call{value: address(this).balance}("");
        require(success);
    }
}
