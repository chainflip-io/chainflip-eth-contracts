# `StateChainGateway`

  Manages the funding and redemption FLIP from/to stateChain accounts.
          Accounts on the FLIP state chain basically have full control
          of FLIP leaving the contract. FLIP can be added to the StateChain
          account via `fundStateChainAccount` with their stateChain nodeID.

          This contract also handles the minting and burning of FLIP after the
          initial supply is minted during FLIP's creation. At any time, a
          valid aggragate signature can be submitted to the contract which
          updates the total supply by minting or burning the necessary FLIP.

## `constructor(contract IKeyManager keyManager, uint256 minFunding)` (public)

No description

## `_getGovernor() → address` (internal)

No description

## `_getCommunityKey() → address` (internal)

No description

## `getFLIP() → contract IFLIP` (external)

 Get the FLIP token address

Returns

- The address of FLIP

## `_checkUpdateKeyManager(contract IKeyManager keyManager, bool omitChecks)` (internal)

No description

## `setFlip(contract IFLIP flip)` (external)

 Sets the FLIP address after initialization. We can't do this in the constructor
         because FLIP contract requires this contract's address on deployment for minting.
         First this contract is deployed, then the FLIP contract and finally setFLIP
         should be called. Deployed via DeployerContract.sol so it can't be frontrun.
         The FLIP address can only be set once.

- `flip`: FLIP token address

## `fundStateChainAccount(bytes32 nodeID, uint256 amount)` (external)

         Add FLIP funds to a StateChain account identified with a nodeID

- `amount`:    The amount of FLIP tokens

- `nodeID`:    The nodeID of the account to fund

## `registerRedemption(struct IShared.SigData sigData, bytes32 nodeID, uint256 amount, address redeemAddress, uint48 expiryTime)` (external)

 Redeem FLIP from the StateChain. The State Chain will determine the amount
         that can be redeemed, but a basic calculation for a validator would be:
         amount redeemable = stake + rewards - penalties.

- `sigData`:   Struct containing the signature data over the message
                 to verify, signed by the aggregate key.

- `nodeID`:    The nodeID of the account redeeming the FLIP

- `amount`:    The amount of funds to be locked up

- `redeemAddress`:    The redeemAddress who will receive the FLIP

- `expiryTime`:   The last valid timestamp that can execute this redemption (uint48)

## `executeRedemption(bytes32 nodeID)` (external)

 Execute a pending redemption to get back funds. Cannot execute a pending
         redemption before 48h have passed after registering it, or after the specified
         expiry time

- `nodeID`:    The nodeID of the funder

## `updateFlipSupply(struct IShared.SigData sigData, uint256 newTotalSupply, uint256 stateChainBlockNumber)` (external)

 Compares a given new FLIP supply against the old supply and mints or burns
         FLIP tokens from this contract as appropriate.
         It requires a message signed by the aggregate key.

- `sigData`:               Struct containing the signature data over the message
                             to verify, signed by the aggregate key.

- `newTotalSupply`:        new total supply of FLIP

- `stateChainBlockNumber`: State Chain block number for the new total supply

## `updateFlipIssuer(struct IShared.SigData sigData, address newIssuer, bool omitChecks)` (external)

 Updates the address that is allowed to issue FLIP tokens. This will be used when this
         contract needs an upgrade. A new contract will be deployed and all the FLIP will be
         transferred to it via the redemption process. Finally the right to issue FLIP will be transferred.

- `sigData`:     Struct containing the signature data over the message
                   to verify, signed by the aggregate key.

- `newIssuer`:   New contract that will issue FLIP tokens.

- `omitChecks`: Allow the omission of the extra checks in a special case

## `setMinFunding(uint256 newMinFunding)` (external)

     Set the minimum amount of funds needed for `fundStateChainAccount` to be able
             to be called. Used to prevent spamming of funding.

- `newMinFunding`:   The new minimum funding amount

## `govWithdraw()` (external)

Withdraw all FLIP to governance address in case of emergency. This withdrawal needs
        to be approved by the Community, it is a last resort. Used to rectify an emergency.
        Transfer the issuance to the governance address if this contract is the issuer.

## `govUpdateFlipIssuer()` (external)

Update the FLIP Issuer address with the governance address in case of emergency.
        This needs to be approved by the Community, it is a last resort. Used to rectify
        an emergency.

## `getMinimumFunding() → uint256` (external)

 Get the minimum amount of funds that's required for funding
         an account on the StateChain.

Returns

- The minimum amount (uint)

## `getPendingRedemption(bytes32 nodeID) → struct IStateChainGateway.Redemption` (external)

 Get the pending redemption for the input nodeID. If there was never
         a pending redemption for this nodeID, or it has already been executed
         (and therefore deleted), it'll return (0, 0x00..., 0, 0)

- `nodeID`:   The nodeID which has a pending redemption

Returns

- The redemption (Redemption struct)

## `getLastSupplyUpdateBlockNumber() → uint256` (external)

 Get the last state chain block number of the last supply update

Returns

- The state chain block number of the last supply update
