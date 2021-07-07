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


## `setEmissionPerBlock(struct IShared.SigData sigData, uint256 newEmissionPerBlock)` (external)

 Set the rate (per second) at which new FLIP is minted to this contract


- `sigData`:   The keccak256 hash over the msg (uint) (which is the calldata
                 for this function with empty msgHash and sig) and sig over that hash
                 from the current governance key (uint)

- `newEmissionPerBlock`:     The new rate


## `setMinStake(struct IShared.SigData sigData, uint256 newMinStake)` (external)

     Set the minimum amount of stake needed for `stake` to be able
             to be called. Used to prevent spamming of stakes.


- `sigData`:   The keccak256 hash over the msg (uint) (which is the calldata
                 for this function with empty msgHash and sig) and sig over that hash
                 from the current governance key (uint)

- `newMinStake`:   The new minimum stake


## `getKeyManager() → contract IKeyManager` (external)

 Get the KeyManager address/interface that's used to validate sigs


Returns

- The KeyManager (IKeyManager)

## `getFLIPAddress() → address` (external)

 Get the FLIP token address


Returns

- The address of FLIP

## `getLastMintBlockNum() → uint256` (external)

 Get the last time that claim() was called, in unix time


Returns

- The time of the last claim (uint)

## `getEmissionPerBlock() → uint256` (external)

 Get the emission rate of FLIP in seconds


Returns

- The rate of FLIP emission (uint)

## `getInflationInFuture(uint256 blocksIntoFuture) → uint256` (external)

 Get the amount of FLIP that would be emitted via inflation at
         the current block plus addition inflation from an extra
         `blocksIntoFuture` blocks


- `blocksIntoFuture`:  The number of blocks past the current block to
             calculate the inflation at


Returns

- The amount of FLIP inflation

## `getTotalStakeInFuture(uint256 blocksIntoFuture) → uint256` (external)

 Get the total amount of FLIP currently staked by all stakers
         plus the inflation that could be minted if someone called
         `claim` or `setEmissionPerBlock` at the specified block


- `blocksIntoFuture`:  The number of blocks into the future added
             onto the current highest block. E.g. if the current highest
             block is 10, and the stake + inflation that you want to know
             is at height 15, input 5


Returns

- The total of stake + inflation at specified blocks in the future from now

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


