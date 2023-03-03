# `Deposit`

  Creates a contract with a known address and withdraws tokens from it.
          After deployment, the Vault will call fetch() to withdraw tokens.

     The logic is not refactored into a single function because it's cheaper.

## `constructor(contract IERC20Lite token)` (public)

No description

## `fetch(contract IERC20Lite token)` (external)

No description

## `receive()` (external)

No description
