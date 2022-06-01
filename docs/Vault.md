# `Vault`

  The vault for holding ETH/tokens and deploying contracts
          for fetching individual deposits




## `validTime()`



   Check that no nonce of the current AggKey has been consumed in the last 14 days - emergency

## `swapsEnabled()`



   Check that swaps are enabled

## `swapsDisabled()`



   Check that swaps are disabled


## `constructor(contract IKeyManager keyManager)` (public)

No description


## `_getGovernor() → address` (internal)

No description


## `_getCommunityKey() → address` (internal)

No description


## `allBatch(struct IShared.SigData sigData, bytes32[] fetchSwapIDs, contract IERC20[] fetchTokens, contract IERC20[] tranTokens, address payable[] tranRecipients, uint256[] tranAmounts)` (external)

 Can do a combination of all fcns in this contract. It first fetches all
         deposits specified with fetchSwapIDs and fetchTokens (which are requried
         to be of equal length), then it performs all transfers specified with the rest
         of the inputs, the same as transferBatch (where all inputs are again required
         to be of equal length - however the lengths of the fetch inputs do not have to
         be equal to lengths of the transfer inputs). Fetches/transfers of ETH are indicated
         with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address. It is assumed
         that the elements of each array match in terms of ordering, i.e. a given
         fetch should should have the same index swapIDs[i] and tokens[i]


- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `fetchSwapIDs`:      The unique identifiers for this swap (bytes32[]), used for create2

- `fetchTokens`:   The addresses of the tokens to be transferred

- `tranTokens`:    The addresses of the tokens to be transferred

- `tranRecipients`:    The address of the recipient of the transfer

- `tranAmounts`:       The amount to transfer, in wei (uint)


## `transfer(struct IShared.SigData sigData, contract IERC20 token, address payable recipient, uint256 amount)` (external)

 Transfers ETH or a token from this vault to a recipient


- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `token`:     The token to be transferred

- `recipient`: The address of the recipient of the transfer

- `amount`:    The amount to transfer, in wei (uint)


## `transferBatch(struct IShared.SigData sigData, contract IERC20[] tokens, address payable[] recipients, uint256[] amounts)` (external)

 Transfers ETH or tokens from this vault to recipients. It is assumed
         that the elements of each array match in terms of ordering, i.e. a given
         transfer should should have the same index tokens[i], recipients[i],
         and amounts[i].


- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `tokens`:    The addresses of the tokens to be transferred

- `recipients`: The address of the recipient of the transfer

- `amounts`:    The amount to transfer, in wei (uint)


## `sendEth(address payable recipient)` (external)

 Annoyingly, doing `try addr.transfer` in `_transfer` fails because
         Solidity doesn't see the `address` type as an external contract
         and so doing try/catch on it won't work. Need to make it an external
         call, and doing `this.something` counts as an external call, but that
         means we need a fcn that just sends eth


- `recipient`: The address to receive the ETH


## `fetchDepositEth(struct IShared.SigData sigData, bytes32 swapID)` (external)

 Retrieves ETH from an address, deterministically generated using
         create2, by creating a contract for that address, sending it to this vault, and
         then destroying


- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `swapID`:    The unique identifier for this swap (bytes32)


## `fetchDepositEthBatch(struct IShared.SigData sigData, bytes32[] swapIDs)` (external)

 Retrieves ETH from multiple addresses, deterministically generated using
         create2, by creating a contract for that address, sending it to this vault, and
         then destroying


- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `swapIDs`:    The unique identifiers for this swap (bytes32)


## `fetchDepositToken(struct IShared.SigData sigData, bytes32 swapID, contract IERC20 token)` (external)

 Retrieves a token from an address deterministically generated using
         create2 by creating a contract for that address, sending it to this vault, and
         then destroying


- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `swapID`:    The unique identifier for this swap (bytes32), used for create2

- `token`:     The token to be transferred


## `fetchDepositTokenBatch(struct IShared.SigData sigData, bytes32[] swapIDs, contract IERC20[] tokens)` (external)

 Retrieves tokens from multiple addresses, deterministically generated using
         create2, by creating a contract for that address, sending it to this vault, and
         then destroying


- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `swapIDs`:       The unique identifiers for this swap (bytes32[]), used for create2

- `tokens`:        The addresses of the tokens to be transferred


## `swapETH(string egressParams, bytes32 egressReceiver)` (external)

 Swaps ETH for a token in another chain. Function call needs to specify egress parameters


- `egressParams`:  String containing egress parameters

- `egressReceiver`:  Egress reciever's address


## `swapToken(string egressParams, bytes32 egressReceiver, address ingressToken, uint256 amount)` (external)

 Swaps ERC20 Token for a token in another chain. Function call needs to specify the ingress and egress parameters


- `egressParams`:  String containing egress parameters

- `egressReceiver`:  Egress reciever's address

- `ingressToken`:  Ingress ERC20 token's address

- `amount`:  Amount of ingress token to swap


## `govWithdraw(contract IERC20[] tokens)` (external)

Withdraw all funds to governance address in case of emergency. This withdrawal needs
        to be approved by the Community and it can only be executed if no nonce from the
        current AggKey had been consumed in _AGG_KEY_TIMEOUT time. It is a last resort and
        can be used to rectify an emergency.


- `tokens`:    The addresses of the tokens to be transferred


## `enableSwaps()` (external)

 Enable swapETH and swapToken functionality by governance. Features disabled by default


## `disableSwaps()` (external)

 Disable swapETH and swapToken functionality by governance. Features disabled by default


## `getSwapsEnabled() → bool` (external)

 Get swapsEnabled


Returns

- The swapsEnableds state

## `receive()` (external)

No description



## `TransferFailed(address payable recipient, uint256 amount, bytes lowLevelData)`






## `SwapETH(uint256 amount, string egressParams, bytes32 egressReceiver)`






## `SwapToken(address ingressToken, uint256 amount, string egressParams, bytes32 egressReceiver)`






