# `IERC20Lite`

  The interface for functions ERC20Lite implements. This is intended to
          be used with DepositNative so that there is as little code that goes into
          it as possible to reduce gas costs since it'll be deployed frequently

     Removed the return bool on the transfer function to avoid reverts on
          non-standard ERC20s.

## `transfer(address, uint256)` (external)

No description

## `balanceOf(address) → uint256` (external)

No description
