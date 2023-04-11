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

## `xSwapToken(uint32 dstChain, bytes dstAddress, uint16 dstToken, contract IERC20 srcToken, uint256 amount)` (external)

No description

## `xSwapNative(uint32 dstChain, bytes dstAddress, uint16 dstToken)` (external)

No description

## `xCallNative(uint32 dstChain, bytes dstAddress, uint16 dstToken, bytes message, uint256 gasAmount, bytes refundAddress)` (external)

No description

## `xCallToken(uint32 dstChain, bytes dstAddress, uint16 dstToken, bytes message, uint256 gasAmount, contract IERC20 srcToken, uint256 amount, bytes refundAddress)` (external)

No description

## `addGasNative(bytes32 swapID)` (external)

No description

## `addGasToken(bytes32 swapID, uint256 amount, contract IERC20 token)` (external)

No description

## `executexSwapAndCall(struct IShared.SigData sigData, struct IShared.TransferParams transferParams, uint32 srcChain, bytes srcAddress, bytes message)` (external)

No description

## `executexCall(struct IShared.SigData sigData, address recipient, uint32 srcChain, bytes srcAddress, bytes message)` (external)

No description

## `govWithdraw(address[] tokens)` (external)

No description
