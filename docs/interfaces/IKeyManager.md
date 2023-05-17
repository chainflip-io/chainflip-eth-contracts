# `IKeyManager`

  The interface for functions KeyManager implements

## `consumeKeyNonce(struct IShared.SigData sigData, bytes32 contractMsgHash)` (external)

No description

## `setAggKeyWithAggKey(struct IShared.SigData sigData, struct IShared.Key newAggKey)` (external)

No description

## `setAggKeyWithGovKey(struct IShared.Key newAggKey)` (external)

No description

## `setGovKeyWithAggKey(struct IShared.SigData sigData, address newGovKey)` (external)

No description

## `setGovKeyWithGovKey(address newGovKey)` (external)

No description

## `setCommKeyWithAggKey(struct IShared.SigData sigData, address newCommKey)` (external)

No description

## `setCommKeyWithCommKey(address newCommKey)` (external)

No description

## `govAction(bytes32 message)` (external)

No description

## `getAggregateKey() → struct IShared.Key` (external)

No description

## `getGovernanceKey() → address` (external)

No description

## `getCommunityKey() → address` (external)

No description

## `isNonceUsedByAggKey(uint256 nonce) → bool` (external)

No description

## `getLastValidateTime() → uint256` (external)

No description

## `AggKeySetByAggKey(struct IShared.Key oldAggKey, struct IShared.Key newAggKey)`

## `AggKeySetByGovKey(struct IShared.Key oldAggKey, struct IShared.Key newAggKey)`

## `GovKeySetByAggKey(address oldGovKey, address newGovKey)`

## `GovKeySetByGovKey(address oldGovKey, address newGovKey)`

## `CommKeySetByAggKey(address oldCommKey, address newCommKey)`

## `CommKeySetByCommKey(address oldCommKey, address newCommKey)`

## `SignatureAccepted(struct IShared.SigData sigData, address signer)`

## `GovernanceAction(bytes32 message)`
