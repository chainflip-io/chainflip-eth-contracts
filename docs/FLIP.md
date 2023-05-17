# `FLIP`

  The FLIP utility token which is used in the StateChain.

## `onlyIssuer()`

   Check that the caller is the token issuer.

## `constructor(uint256 flipTotalSupply, uint256 numGenesisValidators, uint256 genesisStake, address receiverGenesisValidatorFlip, address receiverGenesisFlip, address genesisIssuer)` (public)

No description

## `mint(address account, uint256 amount)` (external)

Mint FLIP tokens to an account. This is controlled via an issuer
        controlled by the StateChain to adjust the supply of FLIP tokens.

- `account`:   Account to receive the newly minted tokens

- `amount`:    Amount of tokens to mint

## `burn(address account, uint256 amount)` (external)

Mint FLIP tokens to an account. This is controlled via an issuer
        controlled by the StateChain to adjust the supply of FLIP tokens.

- `account`:   Account to burn the tokens from

- `amount`:    Amount of tokens to burn

## `updateIssuer(address newIssuer)` (external)

Update the issuer address. This is to be controlled via an issuer
        controlled by the StateChain.

- `newIssuer`:   Account that can mint and burn FLIP tokens.

## `getIssuer() → address` (external)

No description
