# `IStakeManager`

## `stake(bytes32 nodeID, uint256 amount, address returnAddr)` (external)

         Stake some FLIP and attribute it to a nodeID

- `amount`:    The amount of stake to be locked up

- `nodeID`:    The nodeID of the staker

- `returnAddr`:    The address which the staker requires to be used
                     when claiming back FLIP for `nodeID`

## `registerClaim(struct IShared.SigData sigData, bytes32 nodeID, uint256 amount, address staker, uint48 expiryTime)` (external)

 Claim back stake. If only losing an auction, the same amount initially staked
         will be sent back. If losing an auction while being a validator,
         the amount sent back = stake + rewards - penalties, as determined by the State Chain

- `sigData`:   The keccak256 hash over the msg (uint) (which is the calldata
                 for this function with empty msgHash and sig) and sig over that hash
                 from the current aggregate key (uint)

- `nodeID`:    The nodeID of the staker

- `amount`:    The amount of stake to be locked up

- `staker`:    The staker who is to be sent FLIP

- `expiryTime`:   The last valid block height that can execute this claim (uint48)

## `executeClaim(bytes32 nodeID)` (external)

 Execute a pending claim to get back stake. If only losing an auction,
         the same amount initially staked will be sent back. If losing an
         auction while being a validator, the amount sent back = stake +
         rewards - penalties, as determined by the State Chain. Cannot execute a pending
         claim before 48h have passed after registering it, or after the specified
         expiry block height

- `nodeID`:    The nodeID of the staker

## `updateFlipSupply(struct IShared.SigData sigData, uint256 newTotalSupply, uint256 stateChainBlockNumber)` (external)

 Compares a given new FLIP supply against the old supply,
         then mints new and burns as appropriate (to/from the StakeManager)

- `sigData`:               signature over the abi-encoded function params

- `newTotalSupply`:        new total supply of FLIP

- `stateChainBlockNumber`: State Chain block number for the new total supply

## `setMinStake(uint256 newMinStake)` (external)

     Set the minimum amount of stake needed for `stake` to be able
             to be called. Used to prevent spamming of stakes.

- `newMinStake`:   The new minimum stake

## `suspend()` (external)

     Pause claim executions on the contract, for the purpose of
             allowing governance to intervene in an emergency.

## `resume()` (external)

     Resume claim executions on the contract.

## `govWithdraw()` (external)

     Withdraw all FLIP to governance address, only if suspended.
             Used to rectify an emergency. Chainflip network is likely
             to be compromised if this is necessary, it is a last resort.

## `getKeyManager() → contract IKeyManager` (external)

 Get the KeyManager address/interface that's used to validate sigs

Returns

- The KeyManager (IKeyManager)

## `getFLIP() → contract IFLIP` (external)

 Get the FLIP token address

Returns

- The address of FLIP

## `getLastSupplyUpdateBlockNumber() → uint256` (external)

 Get the last state chain block number that the supply was updated at

Returns

- The state chain block number of the last update

## `getMinimumStake() → uint256` (external)

 Get the minimum amount of stake that's required for a bid
         attempt in the auction to be valid - used to prevent sybil attacks

Returns

- The minimum stake (uint)

## `getPendingClaim(bytes32 nodeID) → struct IStakeManager.Claim` (external)

 Get the pending claim for the input nodeID. If there was never
         a pending claim for this nodeID, or it has already been executed
         (and therefore deleted), it'll return (0, 0x00..., 0, 0)

- `nodeID`:    The nodeID which is has a pending claim

Returns

- The claim (Claim)

## `Staked(bytes32 nodeID, uint256 amount, address staker, address returnAddr)`

## `ClaimRegistered(bytes32 nodeID, uint256 amount, address staker, uint48 startTime, uint48 expiryTime)`

## `ClaimExecuted(bytes32 nodeID, uint256 amount)`

## `FlipSupplyUpdated(uint256 oldSupply, uint256 newSupply, uint256 stateChainBlockNumber)`

## `MinStakeChanged(uint256 oldMinStake, uint256 newMinStake)`
