# `TokenVesting`

A token holder contract that that vests its balance of any ERC20 token to the beneficiary.
     Two vesting contract options:
       Option A: Validator lockup - stakable. Nothing unlocked until end of contract where everything
                 unlocks at once. All funds can be staked during the vesting period.
                 If revoked send all funds to revoker and block beneficiary releases indefinitely.
                 Any staked funds at the moment of revocation can be retrieved by the revoker upon unstaking.
       Option B: Linear lockup - not stakable. 20% cliff unlocking and 80% linear after that.
                 If revoked send all funds to revoker and allow beneficiary to release remaining vested funds.

      The reference to the staking contract is hold by the AddressHolder contract to allow for governance to
      update it in case the staking contract needs to be upgraded.

      The vesting schedule is time-based (i.e. using block timestamps as opposed to e.g. block numbers), and
      is therefore sensitive to timestamp manipulation (which is something miners can do, to a certain degree).
      Therefore, it is recommended to avoid using short time durations (less than a minute). Typical vesting
      schemes, with a cliff period of a year and a duration of four years, are safe to use.

## `onlyBeneficiary()`

Ensure that the caller is the beneficiary address

## `onlyRevoker()`

Ensure that the caller is the revoker address

## `constructor(address beneficiary_, address revoker_, uint256 cliff_, uint256 end_, bool canStake_, bool transferableBeneficiary_, contract IAddressHolder addressHolder_)` (public)

No description

- `beneficiary_`: address of the beneficiary to whom vested tokens are transferred

- `revoker_`:   the person with the power to revoke the vesting. Address(0) means it is not revocable.

- `cliff_`: the unix time of the cliff, nothing withdrawable before this

- `end_`: the unix time of the end of the vesting period, everything withdrawable after

- `canStake_`: whether the investor is allowed to use vested funds to stake

- `transferableBeneficiary_`: whether the beneficiary address can be transferred

- `addressHolder_`: the contract holding the reference to the contract to stake to if canStake

## `fundStateChainAccount(bytes32 nodeID, uint256 amount)` (external)

 Funds an account in the statechain with some tokens for the nodeID
         and forces the return address of that to be this contract.

- `nodeID`: the nodeID to fund.

- `amount`: the amount of FLIP out of the current funds in this contract.

## `release(contract IERC20 token)` (external)

Transfers vested tokens to beneficiary.

- `token`: ERC20 token which is being vested.

## `revoke(contract IERC20 token)` (external)

Allows the revoker to revoke the vesting.
        When nonstakable, Tokens already vested remain in the contract
        for the beneficiary to release, the rest are returned to the revoker.
        When stakable, assumption is made that revoked will be called once
        funds are unstaked and sent back to this contract.

- `token`: ERC20 token which is being vested.

## `retrieveRevokedFunds(contract IERC20 token)` (external)

Allows the revoker to retrieve tokens that have been unstaked
        after the revoke function has been called (in canStake contracts).
        Safeguard mechanism in case of unstaking happening after revoke.
        Otherwise funds would be locked. In !canStake contracts all the
        funds are withdrawn once revoked is called, so no need for this

- `token`: ERC20 token which is being vested.

## `transferBeneficiary(address beneficiary_)` (external)

No description

## `transferRevoker(address revoker_)` (external)

No description

## `getBeneficiary() → address` (external)

No description

Returns

- the beneficiary address

## `getRevoker() → address` (external)

No description

Returns

- the revoker address
