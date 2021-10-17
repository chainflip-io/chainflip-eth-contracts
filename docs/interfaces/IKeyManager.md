# `IKeyManager`

  The interface for functions KeyManager implements

## `isUpdatedValidSig(struct IShared.SigData sigData, bytes32 contractMsgHash, enum IShared.KeyID keyID) → bool` (external)

No description

## `setAggKeyWithAggKey(struct IShared.SigData sigData, struct IShared.Key newKey)` (external)

No description

## `setAggKeyWithGovKey(struct IShared.SigData sigData, struct IShared.Key newKey)` (external)

No description

## `setGovKeyWithGovKey(struct IShared.SigData sigData, struct IShared.Key newKey)` (external)

No description

## `getAggregateKey() → struct IShared.Key` (external)

No description

## `getGovernanceKey() → struct IShared.Key` (external)

No description

## `getLastValidateTime() → uint256` (external)

No description

## `isNonceUsedByKey(enum IShared.KeyID keyID, uint256 nonce) → bool` (external)

No description
