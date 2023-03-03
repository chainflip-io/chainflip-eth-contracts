# `IGovernanceCommunityGuarded`

## `enableCommunityGuard()` (external)

 Enable Community Guard

## `disableCommunityGuard()` (external)

 Disable Community Guard

## `suspend()` (external)

 Can be used to suspend contract execution - only executable by
         governance and only to be used in case of emergency.

## `resume()` (external)

     Resume contract execution

## `getCommunityKey() → address` (external)

 Get the Community Key

Returns

- The CommunityKey

## `getCommunityGuardDisabled() → bool` (external)

 Get the Community Guard state

Returns

- The Community Guard state

## `getSuspendedState() → bool` (external)

 Get suspended state

Returns

- The suspended state

## `getGovernor() → address` (external)

 Get governor address

Returns

- The governor address

## `CommunityGuardDisabled(bool communityGuardDisabled)`

## `Suspended(bool suspended)`
