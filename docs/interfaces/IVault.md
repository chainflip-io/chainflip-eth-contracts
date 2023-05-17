# `IVault`

  The interface for functions Vault implements

## `allBatch(struct IShared.SigData sigData, struct IShared.DeployFetchParams[] deployFetchParamsArray, struct IShared.FetchParams[] fetchParamsArray, struct IShared.TransferParams[] transferParamsArray)` (external)

No description

## `transfer(struct IShared.SigData sigData, struct IShared.TransferParams transferParams)` (external)

No description

## `transferBatch(struct IShared.SigData sigData, struct IShared.TransferParams[] transferParamsArray)` (external)

No description

## `deployAndFetchBatch(struct IShared.SigData sigData, struct IShared.DeployFetchParams[] deployFetchParamsArray)` (external)

No description

## `fetchBatch(struct IShared.SigData sigData, struct IShared.FetchParams[] fetchParamsArray)` (external)

No description

## `xSwapToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, contract IERC20 srcToken, uint256 amount, bytes cfParameters)` (external)

No description

## `xSwapNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes cfParameters)` (external)

No description

## `xCallNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes message, uint256 gasAmount, bytes cfParameters)` (external)

No description

## `xCallToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes message, uint256 gasAmount, contract IERC20 srcToken, uint256 amount, bytes cfParameters)` (external)

No description

## `addGasNative(bytes32 swapID)` (external)

No description

## `addGasToken(bytes32 swapID, uint256 amount, contract IERC20 token)` (external)

No description

## `executexSwapAndCall(struct IShared.SigData sigData, struct IShared.TransferParams transferParams, uint32 srcChain, bytes srcAddress, bytes message)` (external)

No description

## `executexCall(struct IShared.SigData sigData, address recipient, uint32 srcChain, bytes srcAddress, bytes message)` (external)

No description

## `executeActions(struct IShared.SigData sigData, struct IShared.TransferParams transferParams, struct IMulticall.Call[] calls, uint256 gasMulticall)` (external)

No description

## `govWithdraw(address[] tokens)` (external)

No description

## `TransferNativeFailed(address payable recipient, uint256 amount)`

## `TransferTokenFailed(address payable recipient, uint256 amount, address token, bytes reason)`

## `SwapNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, uint256 amount, address sender, bytes cfParameters)`

## `SwapToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, address srcToken, uint256 amount, address sender, bytes cfParameters)`

## `XCallNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, uint256 amount, address sender, bytes message, uint256 gasAmount, bytes cfParameters)`

bytes parameters is not indexed because indexing a dynamic type for it to be filtered
     makes it so we won't be able to decode it unless we specifically search for it. If we want
     to filter it and decode it then we would need to have both the indexed and the non-indexed
     version in the event. That is unnecessary.

## `XCallToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, address srcToken, uint256 amount, address sender, bytes message, uint256 gasAmount, bytes cfParameters)`

## `AddGasNative(bytes32 swapID, uint256 amount)`

## `AddGasToken(bytes32 swapID, uint256 amount, address token)`

## `ExecuteActionsFailed(address payable multicallAddress, uint256 amount, address token, bytes reason)`
