# `KeyManager`

  Holds the aggregate and governance keys, functions to update them, and
          consumeKeyNonce so other contracts can verify signatures and updates _lastValidateTime

## `timeoutEmergency()`

   Check that enough time has passed for setAggKeyWithGovKey. Needs
        to be done as a modifier so that it can happen before consumeKeyNonce

## `validAggKey(struct IShared.Key key)`

   Check that an aggregate key is capable of having its signatures
        verified by the schnorr lib.

## `onlyGovernor()`

   Check that the sender is the governance address

## `onlyCommunityKey()`

   Check that the caller is the Community Key address.

## `consumeKeyNonceKeyManager(struct IShared.SigData sigData, bytes32 contractMsgHash)`

   For functions in this contract that require a signature from the aggregate key

## `constructor(struct IShared.Key initialAggKey, address initialGovKey, address initialCommKey)` (public)

No description

## `_consumeKeyNonce(struct IShared.SigData sigData, bytes32 msgHash)` (internal)

 Checks the validity of a signature and msgHash, then updates _lastValidateTime

- `sigData`:   Struct containing the signature data over the message
                 to verify, signed by the aggregate key.

- `msgHash`:   The hash of the message being signed. The hash of the function
                 call parameters is concatenated and hashed together with the nonce, the
                 address of the caller, the chainId, and the address of this contract.

## `consumeKeyNonce(struct IShared.SigData sigData, bytes32 contractMsgHash)` (external)

 Concatenates the contractMsgHash with the nonce, the address of the caller,
         the chainId, and the address of this contract, then hashes that and verifies the
         signature. This is done to prevent replay attacks.

- `sigData`:           Struct containing the signature data over the message
                         to verify, signed by the aggregate key.

- `contractMsgHash`:   The hash of the function's call parameters. This will be hashed
                         over other parameters to prevent replay attacks.

## `setAggKeyWithAggKey(struct IShared.SigData sigData, struct IShared.Key newAggKey)` (external)

 Set a new aggregate key. Requires a signature from the current aggregate key

- `sigData`:   Struct containing the signature data over the message
                 to verify, signed by the aggregate key.

- `newAggKey`: The new aggregate key to be set. The x component of the pubkey (uint256),
                 the parity of the y component (uint8)

## `setAggKeyWithGovKey(struct IShared.Key newAggKey)` (external)

 Set a new aggregate key. Can only be called by the current governance key

- `newAggKey`: The new aggregate key to be set. The x component of the pubkey (uint256),
                 the parity of the y component (uint8)

## `setGovKeyWithAggKey(struct IShared.SigData sigData, address newGovKey)` (external)

 Set a new aggregate key. Requires a signature from the current aggregate key

- `sigData`:   Struct containing the signature data over the message
                 to verify, signed by the aggregate key.

- `newGovKey`: The new governance key to be set.

## `setGovKeyWithGovKey(address newGovKey)` (external)

 Set a new governance key. Can only be called by current governance key

- `newGovKey`:    The new governance key to be set.

## `setCommKeyWithAggKey(struct IShared.SigData sigData, address newCommKey)` (external)

 Set a new community key. Requires a signature from the current aggregate key

- `sigData`:    Struct containing the signature data over the message
                  to verify, signed by the aggregate key.

- `newCommKey`: The new community key to be set.

## `setCommKeyWithCommKey(address newCommKey)` (external)

 Update the Community Key. Can only be called by the current Community Key.

- `newCommKey`:   New Community key address.

## `govAction(bytes32 message)` (external)

Emit an event containing an action message. Can only be called by the governor.

## `getAggregateKey() → struct IShared.Key` (external)

 Get the current aggregate key

Returns

- The Key struct for the aggregate key

## `getGovernanceKey() → address` (external)

 Get the current governance key

Returns

- The Key struct for the governance key

## `getCommunityKey() → address` (external)

 Get the current community key

Returns

- The Key struct for the community key

## `getLastValidateTime() → uint256` (external)

 Get the last time that a function was called which
         required a signature from _aggregateKeyData or_governanceKeyData

Returns

- The last time consumeKeyNonce was called, in unix time (uint256)

## `isNonceUsedByAggKey(uint256 nonce) → bool` (external)

 Get whether or not the specific keyID has used this nonce before
         since it cannot be used again

Returns

- Whether the nonce has already been used (bool)

## `_getGovernanceKey() → address` (internal)

 Get the current governance key

Returns

- The Key struct for the governance key

## `_getCommunityKey() → address` (internal)

 Get the current community key

Returns

- The Key struct for the community key
