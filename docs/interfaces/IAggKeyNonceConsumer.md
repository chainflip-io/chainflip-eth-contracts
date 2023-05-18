# `IAggKeyNonceConsumer`

## `updateKeyManager(struct IShared.SigData sigData, contract IKeyManager keyManager, bool omitChecks)` (external)

 Update KeyManager reference. Used if KeyManager contract is updated

- `sigData`:    Struct containing the signature data over the message
                  to verify, signed by the aggregate key.

- `keyManager`: New KeyManager's address

- `omitChecks`: Allow the omission of the extra checks in a special case

## `getKeyManager() → contract IKeyManager` (external)

 Get the KeyManager address/interface that's used to validate sigs

Returns

- The KeyManager (IKeyManager)

## `UpdatedKeyManager(address keyManager)`
