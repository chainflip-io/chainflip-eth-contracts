# `IERC1820Registry`



Interface of the global ERC1820 Registry, as defined in the
https://eips.ethereum.org/EIPS/eip-1820[EIP]. Accounts may register
implementers for interfaces in this registry, as well as query support.

Implementers may be shared by multiple accounts, and can also implement more
than a single interface for each account. Contracts can implement interfaces
for themselves, but externally-owned accounts (EOA) must delegate this to a
contract.

{IERC165} interfaces can also be queried via the registry.

For an in-depth explanation and source code analysis, see the EIP text.


## `setManager(address account, address newManager)` (external)

No description


## `getManager(address account) → address` (external)

No description


## `setInterfaceImplementer(address account, bytes32 _interfaceHash, address implementer)` (external)

No description


## `getInterfaceImplementer(address account, bytes32 _interfaceHash) → address` (external)

No description


## `interfaceHash(string interfaceName) → bytes32` (external)

No description


## `updateERC165Cache(address account, bytes4 interfaceId)` (external)

Updates the cache with whether the contract implements an ERC165 interface or not.


- `account`: Address of the contract for which to update the cache.

- `interfaceId`: ERC165 interface for which to update the cache.


## `implementsERC165Interface(address account, bytes4 interfaceId) → bool` (external)

Checks whether a contract implements an ERC165 interface or not.
If the result is not cached a direct lookup on the contract address is performed.
If the result is not cached or the cached value is out-of-date, the cache MUST be updated manually by calling
{updateERC165Cache} with the contract address.


- `account`: Address of the contract to check.

- `interfaceId`: ERC165 interface to check.


Returns

- True if `account` implements `interfaceId`, false otherwise.

## `implementsERC165InterfaceNoCache(address account, bytes4 interfaceId) → bool` (external)

Checks whether a contract implements an ERC165 interface or not without using nor updating the cache.


- `account`: Address of the contract to check.

- `interfaceId`: ERC165 interface to check.


Returns

- True if `account` implements `interfaceId`, false otherwise.


## `InterfaceImplementerSet(address account, bytes32 interfaceHash, address implementer)`






## `ManagerChanged(address account, address newManager)`






