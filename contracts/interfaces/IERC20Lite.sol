// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
 * @title    ERC20 Interface
 * @notice   The interface for functions ERC20Lite implements. This is intended to
 *           be used only in the Deposit contract.
 * @dev      Removed the return bool on the transfer function to avoid reverts on
 *           non-standard ERC20s.
 * @dev      Any change in this contract, including comments, will affect the final
 *           bytecode and therefore will affect the create2 derived addresses.
 *           Do NOT modify unless the consequences of doing so are fully understood.
 */
interface IERC20Lite {
    // Taken from OZ:
    /**
     * @dev Moves `amount` tokens from the caller's account to `recipient`.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address, uint256) external;

    // Taken from OZ:
    /**
     * @dev Returns the amount of tokens owned by `account`.
     */
    function balanceOf(address) external view returns (uint256);
}
