# `VaultEchidna`

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

## `xSwapNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes cfParameters)` (external)

No description

## `xSwapToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, contract IERC20 srcToken, uint256 amount, bytes cfParameters)` (external)

No description

## `xCallNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes message, uint256 dstNativeGas, bytes cfParameters)` (external)

No description

## `xCallToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes message, uint256 dstNativeGas, contract IERC20 srcToken, uint256 amount, bytes cfParameters)` (external)

No description

## `executexSwapAndCall(struct IShared.SigData sigData, struct IShared.TransferParams transferParams, uint32 srcChain, bytes srcAddress, bytes message)` (external)

No description

## `executexCall(struct IShared.SigData sigData, address recipient, uint32 srcChain, bytes srcAddress, bytes message)` (external)

No description

## `govWithdraw(address[] tokens)` (external)

No description

## `updateKeyManagerVault(struct IShared.SigData sigData, contract IKeyManager keyManager, bool omitChecks)` (external)

No description

## `enableCommunityGuardVault()` (external)

No description

## `disableCommunityGuardVault()` (external)

No description

## `suspendVault()` (external)

No description

## `resumeVault()` (external)

No description
