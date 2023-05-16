# `DexAggSrcChainMock`

     Mock implementation of a DEX Aggregator for testing purposes. There are three
          mocks in this file: the DEX Aggregator contract on the source chain, the one on
          the destination chain, and the mock DEX contract called on the destination chain.
          The flow is as follows:
          Native:Chain1 (User to Vault) -> Token:Chain2 (CF swap) -> Token2:Chain2 (DexMock swap)
          The DexMockSwap parameters are encoded on the srcChain as part of the message and decoded
          on the dstChain.
          This contract is a Mock and this is not the actual implementation of a DEX Aggregator.
          The contract is only for testing purposes to do a proof of concept of a full cross-chain
          swap with a DEX Aggregator, do not inherit nor use in production.

## `constructor(address _cfVault)` (public)

No description

## `swapNativeAndCallViaChainflip(uint32 dstChain, bytes dstAddress, uint32 dstToken, address dexAddress, address dstTokenAddr, address userToken, address userAddress)` (external)

No description

## `swapTokenAndCallViaChainflip(uint32 dstChain, bytes dstAddress, uint32 dstToken, address dexAddress, address dstTokenAddr, address userToken, address userAddress, address srcToken, uint256 srcAmount)` (external)

No description
