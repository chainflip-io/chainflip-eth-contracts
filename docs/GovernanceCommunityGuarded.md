# `GovernanceCommunityGuarded`

  Allows the governor to perform certain actions for the procotol's safety in
          case of emergency. The aim is to allow the governor to suspend execution of
          critical functions.
          Also, it allows the CommunityKey to safeguard certain functions so the
          governor can execute them iff the communityKey allows it.

## `isCommunityKey()`

   Check that the caller is the Community Key address.

## `isCommunityGuardDisabled()`

   Check that community has disabled the community guard.

## `isCommunityGuardEnabled()`

   Check that community has disabled the community guard.

## `isGovernor()`

Ensure that the caller is the governor address. Calls the getGovernor
        function which is implemented by the children.

## `isSuspended()`

## `isNotSuspended()`

## `_getGovernor() → address` (internal)

 Get the governor's address. The contracts inheriting this (StakeManager and Vault)
         get the governor's address from the KeyManager through the AggKeyNonceConsumer's
         inheritance. Therefore, the implementation of this function must be left
         to the children. This is a workaround since the isGovernor modifier can't be
         made virtual. This contract needs to be marked as abstract.

Returns

- The governor's address

## `_getCommunityKey() → address` (internal)

 Get the community's address. The contracts inheriting this (StakeManager and Vault)
         get the community's address from the KeyManager through the AggKeyNonceConsumer's
         inheritance. Therefore, the implementation of this function must be left
         to the children. This is a workaround since the isCommunityKey modifier can't be
         made virtual. This contract needs to be marked as abstract.

Returns

- The community's address

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

## `getCommunityGuard() → bool` (external)

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
