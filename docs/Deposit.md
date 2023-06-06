# `Deposit`

  Creates a contract with a known address and withdraws tokens from it.
          After deployment, the Vault will call fetch() to withdraw tokens.

     Any change in this contract, including comments, will affect the final
          bytecode and therefore will affect the create2 derived addresses.
          Do NOT modify unless the consequences of doing so are fully understood.

## `constructor(address token)` (public)

No description

## `fetch(address token)` (external)

No description

## `receive()` (external)

No description

## `FetchedNative(uint256 amount)`
