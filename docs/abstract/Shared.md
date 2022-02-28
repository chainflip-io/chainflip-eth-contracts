# `Shared`

  Holds constants and modifiers that are used in multiple contracts

     It would be nice if this could be a library, but modifiers can't be exported :(

## `nzUint(uint256 u)`

   Checks that a uint isn't zero/empty

## `nzAddr(address a)`

   Checks that an address isn't zero/empty

## `nzBytes32(bytes32 b)`

   Checks that a bytes32 isn't zero/empty

## `nzKey(struct IShared.Key key)`

   Checks that the pubKeyX is populated

## `refundGas()`

   Refunds (almost all) the gas spend to call this function

## `refundEth(address to, uint256 amount)` (external)

No description

## `Refunded(uint256 amount)`

## `RefundFailed(address to, uint256 amount, uint256 currentBalance)`
