# `IKeyManager`

  The interface for functions KeyManager implements

## `isUpdatedValidSig(struct IShared.SigData sigData, bytes32 contractMsgHash) → bool` (external)

No description

## `setAggKeyWithAggKey(struct IShared.SigData sigData, struct IShared.Key newKey)` (external)

No description

## `setAggKeyWithGovKey(struct IShared.Key newKey)` (external)

No description

## `setGovKeyWithGovKey(address newKey)` (external)

No description

## `canValidateSig(address addr) → bool` (external)

No description

## `canValidateSigSet() → bool` (external)

No description

## `getAggregateKey() → struct IShared.Key` (external)

No description

## `getGovernanceKey() → address` (external)

No description

## `getLastValidateTime() → uint256` (external)

No description

## `isNonceUsedByAggKey(uint256 nonce) → bool` (external)

No description

## `AggKeySetByAggKey(struct IShared.Key oldKey, struct IShared.Key newKey)`

## `AggKeySetByGovKey(struct IShared.Key oldKey, struct IShared.Key newKey)`

## `GovKeySetByGovKey(address oldKey, address newKey)`

## `SignatureAccepted(struct IShared.SigData sigData, address broadcaster)`
