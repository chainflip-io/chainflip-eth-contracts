# `ICFReceiver`

     The ICFReceiver interface is the interface required to receive tokens and
          cross-chain calls from the Chainflip Protocol.

## `cfReceive(uint32 srcChain, bytes srcAddress, bytes message, address token, uint256 amount)` (external)

 Receiver of a cross-chain swap and call made by the Chainflip Protocol.

- `srcChain`:      The source chain according to the Chainflip Protocol's nomenclature.

- `srcAddress`:    Bytes containing the source address on the source chain.

- `message`:       The message sent on the source chain. This is a general purpose message.

- `token`:         Address of the token received. _NATIVE_ADDR if it's native tokens.

- `amount`:        Amount of tokens received. This will match msg.value for native tokens.

## `cfReceivexCall(uint32 srcChain, bytes srcAddress, bytes message)` (external)

 Receiver of a cross-chain call made by the Chainflip Protocol.

- `srcChain`:      The source chain according to the Chainflip Protocol's nomenclature.

- `srcAddress`:    Bytes containing the source address on the source chain.

- `message`:       The message sent on the source chain. This is a general purpose message.
