# `IFLIP`

## `updateFlipSupply(struct IShared.SigData sigData, uint256 newTotalSupply, uint256 stateChainBlockNumber, address staker)` (external)

 Compares a given new FLIP supply against the old supply,
         then mints and burns as appropriate

- `sigData`:               signature over the abi-encoded function params

- `newTotalSupply`:        new total supply of FLIP

- `stateChainBlockNumber`: State Chain block number for the new total supply

- `staker`: Staking contract owner of the tokens to be minted/burnt

## `getLastSupplyUpdateBlockNumber() → uint256` (external)

 Get the last state chain block number that the supply was updated at

Returns

- The state chain block number of the last update

## `FlipSupplyUpdated(uint256 oldSupply, uint256 newSupply, uint256 stateChainBlockNumber)`
