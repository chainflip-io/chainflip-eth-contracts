# `StakeManager`

  Manages the staking of FLIP. Validators on the FLIP state chain
          basically have full control of FLIP leaving the contract. Auction
          logic for validator slots is not handled in this contract - bidders
          just send their bid to this contract via `stake` with their FLIP state chain
          nodeID, the ChainFlip Engine witnesses the bids, takes the top n bids,
          assigns them to slots, then signs/calls `claim` to refund everyone else.

          This contract also handles the minting of FLIP after the initial supply
          is minted during FLIP's creation. Every new block after the contract is created is
          able to mint `_emissionPerBlock` amount of FLIP. This is FLIP that's meant to 
          be rewarded to validators for their service. If none of them end up being naughty
          boys or girls, then their proportion of that newly minted reward will be rewarded
          to them based on their proportion of the total stake when they `claim` - though the logic of
          assigning rewards is handled by the ChainFlip Engine via aggKey and this contract just blindly
          trusts its judgement. There is an intentional limit on the power to mint, which is
          why there's an emission rate controlled within the contract, so that a compromised
          aggKey can't mint infinite tokens - the most that can be minted is any outstanding
          emission of FLIP and the most that can be stolen is the FLIP balance of this contract,
          which is the total staked (or bidded during auctions) + total emitted from rewards.
          However, a compromised govKey could change the emission rate and therefore mint
          infinite tokens.




## `validSig(struct IShared.SigData sigData, bytes32 contractMsgHash, enum IShared.KeyID keyID)`



   Call isValidSig in _keyManager

## `noFish()`

Ensure that FLIP can only be withdrawn via `claim`
        and not any other method




## `constructor(contract IKeyManager keyManager, uint256 emissionPerBlock, uint256 minStake, uint256 flipTotalSupply)` (public)

No description


## `stake(uint256 nodeID, uint256 amount)` (external)

         Stake some FLIP and attribute it to a nodeID


- `amount`:    The amount of stake to be locked up

- `nodeID`:    The nodeID of the staker


## `claim(struct IShared.SigData sigData, uint256 nodeID, address staker, uint256 amount)` (external)

 Claim back stake. If only losing an auction, the same amount initially staked
         will be sent back. If losing an auction while being a validator,
                the amount sent back = stake + rewards - penalties, as determined by the CFE


- `sigData`:   The keccak256 hash over the msg (uint) (which is the calldata
                 for this function with empty msgHash and sig) and sig over that hash
                 from the current aggregate key (uint)

- `nodeID`:    The nodeID of the staker

- `staker`:    The staker who is to be sent FLIP

- `amount`:    The amount of stake to be locked up


## `claimBatch(struct IShared.SigData sigData, uint256[] nodeIDs, address[] stakers, uint256[] amounts)` (external)

 Claim back stakes in a batch. If only losing an auction, the same amount
         initially staked will be sent back. If losing an auction while being a validator,
         the amount sent back = stake + rewards - penalties, as determined by the CFE.
         It is assumed that the elements of each array match in terms of ordering,
         i.e. a given transfer should should have the same index tokenAddrs[i],
         recipients[i], and amounts[i].


- `sigData`:   The keccak256 hash over the msg (uint) (which is the calldata
                 for this function with empty msgHash and sig) and sig over that hash
                 from the current aggregate key (uint)

- `nodeIDs`:   The nodeIDs of the stakers

- `stakers`:   The stakers who are to be sent FLIP

- `amounts`:   The amounts of stake to be locked up


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

## `getInflationInFuture(uint256 blocksIntoFuture) → uint256` (public)

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


## `Staked(uint256 nodeID, uint256 amount)`






## `Claimed(uint256 nodeID, uint256 amount)`






## `EmissionChanged(uint256 oldEmissionPerBlock, uint256 newEmissionPerBlock)`






## `MinStakeChanged(uint256 oldMinStake, uint256 newMinStake)`






