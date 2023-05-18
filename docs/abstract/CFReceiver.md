# `CFReceiver`

     This abstract contract is the base implementation for a smart contract
          capable of receiving cross-chain swaps and calls from the Chainflip Protocol.
          It has a check to ensure that the functions can only be called by one
          address, which should be the Chainflip Protocol. This way it is ensured that
          the receiver will be sent the amount of tokens passed as parameters and
          that the cross-chain call originates from the srcChain and address specified.
          This contract should be inherited and then user's logic should be implemented
          as the internal functions (_cfReceive and _cfReceivexCall).
          Remember that anyone on the source chain can use the Chainflip Protocol
          to make a cross-chain call to this contract. If that is not desired, an extra
          check on the source address and source chain should be performed.

## `onlyCfVault()`

Check that the sender is the Chainflip's Vault.

## `onlyOwner()`

Check that the sender is the owner.

## `constructor(address _cfVault)` (internal)

No description

## `cfReceive(uint32 srcChain, bytes srcAddress, bytes message, address token, uint256 amount)` (external)

 Receiver of a cross-chain swap and call made by the Chainflip Protocol.

- `srcChain`:      The source chain according to the Chainflip Protocol's nomenclature.

- `srcAddress`:    Bytes containing the source address on the source chain.

- `message`:       The message sent on the source chain. This is a general purpose message.

- `token`:         Address of the token received. _NATIVE_ADDR if native.

- `amount`:        Amount of tokens received. This will match msg.value for native tokens.

## `cfReceivexCall(uint32 srcChain, bytes srcAddress, bytes message)` (external)

 Receiver of a cross-chain call made by the Chainflip Protocol.

- `srcChain`:      The source chain according to the Chainflip Protocol's nomenclature.

- `srcAddress`:    Bytes containing the source address on the source chain.

- `message`:       The message sent on the source chain. This is a general purpose message.

## `_cfReceive(uint32 srcChain, bytes srcAddress, bytes message, address token, uint256 amount)` (internal)

No description

## `_cfReceivexCall(uint32 srcChain, bytes srcAddress, bytes message)` (internal)

No description

## `updateCfVault(address _cfVault)` (external)

          Update Chanflip's Vault address.

- `_cfVault`:    New Chainflip's Vault address.
