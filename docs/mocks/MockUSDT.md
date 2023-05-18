# `MockUSDT`

Implementation of the {IERC20} interface modifying the transfer function
to not return a boolean value.

## `constructor(string name_, string symbol_, uint256 mintAmount_)` (public)

No description

## `name() → string` (public)

No description

## `symbol() → string` (public)

No description

## `decimals() → uint8` (public)

No description

## `totalSupply() → uint256` (public)

No description

## `balanceOf(address account) → uint256` (public)

No description

## `transfer(address recipient, uint256 amount)` (public)

No description

## `allowance(address owner, address spender) → uint256` (public)

No description

## `approve(address spender, uint256 amount) → bool` (public)

No description

## `transferFrom(address sender, address recipient, uint256 amount)` (public)

No description

## `increaseAllowance(address spender, uint256 addedValue) → bool` (public)

No description

## `decreaseAllowance(address spender, uint256 subtractedValue) → bool` (public)

No description

## `_transfer(address sender, address recipient, uint256 amount)` (internal)

No description

## `_mint(address account, uint256 amount)` (internal)

No description

## `_burn(address account, uint256 amount)` (internal)

No description

## `_approve(address owner, address spender, uint256 amount)` (internal)

No description

## `_beforeTokenTransfer(address from, address to, uint256 amount)` (internal)

No description

## `Transfer(address from, address to, uint256 value)`

## `Approval(address owner, address spender, uint256 value)`
