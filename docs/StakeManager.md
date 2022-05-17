# `StakeManager`

  Manages the staking of FLIP. Validators on the FLIP state chain
          basically have full control of FLIP leaving the contract. Bidders
          send their bid to this contract via `stake` with their state chain
          nodeID.

          This contract also handles the minting and burning of FLIP after the
          initial supply is minted during FLIP's creation. At any time, a
          valid aggragate signature can be submitted to the contract which
          updates the total supply by minting or burning the necessary FLIP.

## `updatedValidSig(struct IShared.SigData sigData, bytes32 contractMsgHash)`

   Call isUpdatedValidSig in _keyManager

## `isGovernor()`

Ensure that the caller is the KeyManager's governor address.

## `noFish()`

Ensure that FLIP can only be withdrawn via `claim`
        and not any other method

## `constructor(contract IKeyManager keyManager, uint256 minStake, uint256 flipTotalSupply, uint256 numGenesisValidators, uint256 genesisStake)` (public)

No description

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
         expiry time

- `nodeID`:    The nodeID of the staker

## `updateFlipSupply(struct IShared.SigData sigData, uint256 newTotalSupply, uint256 stateChainBlockNumber)` (external)

 Compares a given new FLIP supply against the old supply,
         then mints and burns as appropriate

- `sigData`:               signature over the abi-encoded function params

- `newTotalSupply`:        new total supply of FLIP

- `stateChainBlockNumber`: State Chain block number for the new total supply

## `setMinStake(uint256 newMinStake)` (external)

     Set the minimum amount of stake needed for `stake` to be able
             to be called. Used to prevent spamming of stakes.

- `newMinStake`:   The new minimum stake

## `tokensReceived(address _operator, address _from, address _to, uint256 _amount, bytes _data, bytes _operatorData)` (external)

     ERC1820 tokensReceived callback, doesn't do anything in our
             contract.

- `_operator`:         operator

- `_from`:             from

- `_to`:               to

- `_amount`:           amount

- `_data`:             data

- `_operatorData`:     operatorData

## `suspend()` (external)

Can be used to suspend executions of claims - only executable by
governance and should only be used if fraudulent claim is suspected.

## `resume()` (external)

Can be used by governance to resume the execution of claims.

## `govWithdraw()` (external)

In the event of fraudulent claims being accepted, the contract is
effectively useless. This function allows governance to admit that by
withdrawing all the FLIP to their address. From where it will be dealt
with later.

## `receive()` (external)

 @notice Allows this contract to receive ETH used to refund callers

## `getKeyManager() → contract IKeyManager` (external)

 Get the KeyManager address/interface that's used to validate sigs

Returns

- The KeyManager (IKeyManager)

## `getFLIP() → contract IFLIP` (external)

 Get the FLIP token address

Returns

- The address of FLIP

## `getLastSupplyUpdateBlockNumber() → uint256` (external)

 Get the last state chain block number of the last supply update

Returns

- The state chain block number of the last supply update

## `getMinimumStake() → uint256` (external)

 Get the minimum amount of stake that's required for a bid
         attempt in the auction to be valid - used to prevent sybil attacks

Returns

- The minimum stake (uint)

## `getPendingClaim(bytes32 nodeID) → struct IStakeManager.Claim` (external)

 Get the pending claim for the input nodeID. If there was never
         a pending claim for this nodeID, or it has already been executed
         (and therefore deleted), it'll return (0, 0x00..., 0, 0)

Returns

- The claim (Claim)
