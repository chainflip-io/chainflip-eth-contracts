# `IVault`

  The interface for functions Vault implements





## `allBatch(struct IShared.SigData sigData, bytes32[] fetchSwapIDs, address[] fetchTokenAddrs, address[] tranTokenAddrs, address payable[] tranRecipients, uint256[] tranAmounts)` (external)

No description


## `transfer(struct IShared.SigData sigData, address tokenAddr, address payable recipient, uint256 amount)` (external)

No description


## `transferBatch(struct IShared.SigData sigData, address[] tokenAddrs, address payable[] recipients, uint256[] amounts)` (external)

No description


## `fetchDepositEth(struct IShared.SigData sigData, bytes32 swapID)` (external)

No description


## `fetchDepositEthBatch(struct IShared.SigData sigData, bytes32[] swapIDs)` (external)

No description


## `fetchDepositToken(struct IShared.SigData sigData, bytes32 swapID, address tokenAddr)` (external)

No description


## `fetchDepositTokenBatch(struct IShared.SigData sigData, bytes32[] swapIDs, address[] tokenAddrs)` (external)

No description


## `getKeyManager() → contract IKeyManager` (external)

No description



