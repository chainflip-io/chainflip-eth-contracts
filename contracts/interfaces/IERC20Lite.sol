pragma solidity ^0.8.0;

/**
 * @title    ERC20 Interface
 * @notice   The interface for functions ERC20Lite implements. This is intended to
 *           be used with DepositNative so that there is as little code that goes into
 *           it as possible to reduce gas costs since it'll be deployed frequently
 * @dev      Removed the return bool on the transfer function to avoid reverts on
 *           non-standard ERC20s.
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
