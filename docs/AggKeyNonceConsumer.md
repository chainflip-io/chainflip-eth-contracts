# `AggKeyNonceConsumer`

  Manages the reference to the KeyManager contract. The address
          is set in the constructor and can only be updated with a valid
          signature validated by the current KeyManager contract. This shall
          be done if the KeyManager contract is updated.

## `consumesKeyNonce(struct IShared.SigData sigData, bytes32 contractMsgHash)`

   Calls consumeKeyNonce in _keyManager

## `constructor(contract IKeyManager keyManager)` (public)

No description

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

## `_getKeyManager() → contract IKeyManager` (internal)

 Internal getter so child contracts can access the _keyManager reference
         but cannot modify it as it is kept private.

Returns

- The KeyManager (IKeyManager)
