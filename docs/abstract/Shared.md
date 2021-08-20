# `Shared`

  Holds constants and modifiers that are used in multiple contracts

     It would be nice if this could be a library, but modifiers can't be exported :(

## `nzUint(uint256 u)`

   Checks that a uint isn't nonzero/empty

## `nzAddr(address a)`

   Checks that an address isn't nonzero/empty

## `nzBytes32(bytes32 b)`

   Checks that a bytes32 isn't nonzero/empty

## `nzKey(struct IShared.Key key)`

   Checks that all of a Key's values are populated
