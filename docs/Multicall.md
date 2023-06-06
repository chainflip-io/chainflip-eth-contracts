# `Multicall`

     This contract is called by the Chainflip Vault to execute actions on behalf of the
          the Vault but in a separate contract to minimize risks.
          This contract is immutable and if the Chainflip Vault is upgraded to a new contract
          this contract will also need to be redeployed. This is to prevent any changes of
          behaviour in this contract while the Vault is making calls to it.
          This contract is based on the SquidMulticall contract from the SquidRouter protocol
          with an added layer of access control. There is also an extra _safeTransferFrom()
          since this contract will get the tokens approved by the Vault instead of transferred.

## `onlyCfVault()`

Check that the sender is the Chainflip's Vault.

## `constructor(address _cfVault)` (public)

No description

## `run(struct IMulticall.Call[] calls, address tokenIn, uint256 amountIn)` (external)

No description

## `supportsInterface(bytes4 interfaceId) → bool` (external)

No description

## `onERC721Received(address, address, uint256, bytes) → bytes4` (external)

No description

## `onERC1155Received(address, address, uint256, uint256, bytes) → bytes4` (external)

No description

## `onERC1155BatchReceived(address, address, uint256[], uint256[], bytes) → bytes4` (external)

No description

## `receive()` (external)

No description
