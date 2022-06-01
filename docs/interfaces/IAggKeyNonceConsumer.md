# `IAggKeyNonceConsumer`

## `updateKeyManager(struct IShared.SigData sigData, contract IKeyManager keyManager)` (external)

 Update KeyManager reference. Used if KeyManager contract is updated

- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `keyManager`: New KeyManager's address

## `getKeyManager() → contract IKeyManager` (external)

 Get the KeyManager address/interface that's used to validate sigs

Returns

- The KeyManager (IKeyManager)
