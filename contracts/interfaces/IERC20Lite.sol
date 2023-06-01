// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/**
 * @title    ERC20 Lite Interface
 * @notice   The interface for functions ERC20Lite implements. This is intended to
 *           be used only in the Deposit contract.
 * @dev      Any change in this contract, including comments, will affect the final
 *           bytecode and therefore will affect the create2 derived addresses.
 *           Do NOT modify unless the consequences of doing so are fully understood.
 */
interface IERC20Lite {
    /// @dev Removed the return bool to avoid reverts on non-standard ERC20s.
    function transfer(address, uint256) external;

    function balanceOf(address) external view returns (uint256);
}
