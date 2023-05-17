# `AggKeyNonceConsumer`

  Manages the reference to the KeyManager contract. The address
          is set in the constructor and can only be updated with a valid
          signature validated by the current KeyManager contract. This shall
          be done if the KeyManager contract is updated.

## `consumesKeyNonce(struct IShared.SigData sigData, bytes32 contractMsgHash)`

   Calls consumeKeyNonce in _keyManager

## `constructor(contract IKeyManager keyManager)` (internal)

No description

## `updateKeyManager(struct IShared.SigData sigData, contract IKeyManager keyManager, bool omitChecks)` (external)

 Update KeyManager reference. Used if KeyManager contract is updated

- `sigData`:    Struct containing the signature data over the message
                  to verify, signed by the aggregate key.

- `keyManager`: New KeyManager's address

- `omitChecks`: Allow the omission of the extra checks in a special case

## `_checkUpdateKeyManager(contract IKeyManager keyManager, bool omitChecks)` (internal)

No description

## `getKeyManager() → contract IKeyManager` (public)

 Get the KeyManager address/interface that's used to validate sigs

Returns

- The KeyManager (IKeyManager)
