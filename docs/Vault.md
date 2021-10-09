# `Vault`

  The vault for holding ETH/tokens and deploying contracts
          for fetching individual deposits




## `validSig(struct IShared.SigData sigData, bytes32 contractMsgHash, enum IShared.KeyID keyID)`



   Calls isUpdatedValidSig in _keyManager


## `constructor(contract IKeyManager keyManager)` (public)

No description


## `allBatch(struct IShared.SigData sigData, bytes32[] fetchSwapIDs, address[] fetchTokenAddrs, address[] tranTokenAddrs, address payable[] tranRecipients, uint256[] tranAmounts)` (external)

 Can do a combination of all fcns in this contract. It first fetches all
         deposits specified with fetchSwapIDs and fetchTokenAddrs (which are requried
         to be of equal length), then it performs all transfers specified with the rest
         of the inputs, the same as transferBatch (where all inputs are again required
         to be of equal length - however the lengths of the fetch inputs do not have to
         be equal to lengths of the transfer inputs). Fetches/transfers of ETH are indicated
         with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address. It is assumed
         that the elements of each array match in terms of ordering, i.e. a given
         fetch should should have the same index swapIDs[i] and tokenAddrs[i]


- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `fetchSwapIDs`:      The unique identifiers for this swap (bytes32[]), used for create2

- `fetchTokenAddrs`:   The addresses of the tokens to be transferred

- `tranTokenAddrs`:    The addresses of the tokens to be transferred

- `tranRecipients`:    The address of the recipient of the transfer

- `tranAmounts`:       The amount to transfer, in wei (uint)


## `transfer(struct IShared.SigData sigData, address tokenAddr, address payable recipient, uint256 amount)` (external)

 Transfers ETH or a token from this vault to a recipient


- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `tokenAddr`: The address of the token to be transferred

- `recipient`: The address of the recipient of the transfer

- `amount`:    The amount to transfer, in wei (uint)


## `transferBatch(struct IShared.SigData sigData, address[] tokenAddrs, address payable[] recipients, uint256[] amounts)` (external)

 Transfers ETH or tokens from this vault to recipients. It is assumed
         that the elements of each array match in terms of ordering, i.e. a given
         transfer should should have the same index tokenAddrs[i], recipients[i],
         and amounts[i].


- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `tokenAddrs`: The addresses of the tokens to be transferred

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


## `fetchDepositToken(struct IShared.SigData sigData, bytes32 swapID, address tokenAddr)` (external)

 Retrieves a token from an address deterministically generated using
         create2 by creating a contract for that address, sending it to this vault, and
         then destroying


- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `swapID`:    The unique identifier for this swap (bytes32), used for create2

- `tokenAddr`: The address of the token to be transferred


## `fetchDepositTokenBatch(struct IShared.SigData sigData, bytes32[] swapIDs, address[] tokenAddrs)` (external)

 Retrieves tokens from multiple addresses, deterministically generated using
         create2, by creating a contract for that address, sending it to this vault, and
         then destroying


- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `swapIDs`:       The unique identifiers for this swap (bytes32[]), used for create2

- `tokenAddrs`:    The addresses of the tokens to be transferred


## `getKeyManager() → contract IKeyManager` (external)

 Get the KeyManager address/interface that's used to validate sigs


Returns

- The KeyManager (IKeyManager)

## `receive()` (external)

No description



## `TransferFailed(address payable recipient, uint256 amount, bytes lowLevelData)`






