# `AddressHolder`

A contract that holds a reference to an address. This reference address can only be updated
     by the governor. This can be used when multiple contracts hold a reference to an address that
     may need to be updated. In that case, it is easier to have a single contract that holds the
     reference address.

## `onlyGovernor()`

Ensure that the caller is the governor address.

## `constructor(address _governor, address _referenceAddress)` (public)

No description

## `updateReferenceAddress(address _referenceAddress)` (external)

No description

## `transferGovernor(address _governor)` (external)

No description

## `getReferenceAddress() → address` (external)

No description

## `getGovernor() → address` (external)

No description
