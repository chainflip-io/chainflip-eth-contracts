# `TokenVesting`

A token holder contract that can release its token balance gradually like a
typical vesting scheme, with a cliff and vesting period. Optionally revocable by the
owner.

## `onlyBeneficiary()`

Ensure that the caller is the beneficiary address

## `onlyRevoker()`

Ensure that the caller is the revoker address

## `constructor(address beneficiary_, address revoker_, uint256 cliff_, uint256 end_, bool canStake_, contract IStakeManager stakeManager_)` (public)

No description

- `beneficiary_`: address of the beneficiary to whom vested tokens are transferred

- `revoker_`:   the person with the power to revoke the vesting. Address(0) means it is not revocable.

- `cliff_`: the unix time of the cliff, nothing withdrawable before this

- `end_`: the unix time of the end of the vesting period, everything withdrawable after

- `canStake_`: whether the investor is allowed to use vested funds to stake

- `stakeManager_`: the staking contract to stake to if canStake

## `stake(bytes32 nodeID, uint256 amount)` (external)

 stakes some tokens for the nodeID and forces the return
         address of that stake to be this contract.

- `nodeID`: the nodeID to stake for.

- `amount`: the amount to stake out of the current funds in this contract.

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

## `TokensReleased(contract IERC20 token, uint256 amount)`

## `TokenVestingRevoked(contract IERC20 token, uint256 refund)`
