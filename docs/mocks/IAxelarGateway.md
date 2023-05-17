# `IAxelarGateway`

## `sendToken(string destinationChain, string destinationAddress, string symbol, uint256 amount)` (external)

No description

## `callContract(string destinationChain, string contractAddress, bytes payload)` (external)

No description

## `callContractWithToken(string destinationChain, string contractAddress, bytes payload, string symbol, uint256 amount)` (external)

No description

## `isContractCallApproved(bytes32 commandId, string sourceChain, string sourceAddress, address contractAddress, bytes32 payloadHash) → bool` (external)

No description

## `isContractCallAndMintApproved(bytes32 commandId, string sourceChain, string sourceAddress, address contractAddress, bytes32 payloadHash, string symbol, uint256 amount) → bool` (external)

No description

## `validateContractCall(bytes32 commandId, string sourceChain, string sourceAddress, bytes32 payloadHash) → bool` (external)

No description

## `validateContractCallAndMint(bytes32 commandId, string sourceChain, string sourceAddress, bytes32 payloadHash, string symbol, uint256 amount) → bool` (external)

No description

## `authModule() → address` (external)

No description

## `tokenDeployer() → address` (external)

No description

## `tokenMintLimit(string symbol) → uint256` (external)

No description

## `tokenMintAmount(string symbol) → uint256` (external)

No description

## `allTokensFrozen() → bool` (external)

No description

## `implementation() → address` (external)

No description

## `tokenAddresses(string symbol) → address` (external)

No description

## `tokenFrozen(string symbol) → bool` (external)

No description

## `isCommandExecuted(bytes32 commandId) → bool` (external)

No description

## `adminEpoch() → uint256` (external)

No description

## `adminThreshold(uint256 epoch) → uint256` (external)

No description

## `admins(uint256 epoch) → address[]` (external)

No description

## `setTokenMintLimits(string[] symbols, uint256[] limits)` (external)

No description

## `upgrade(address newImplementation, bytes32 newImplementationCodeHash, bytes setupParams)` (external)

No description

## `setup(bytes params)` (external)

No description

## `execute(bytes input)` (external)

No description

## `TokenSent(address sender, string destinationChain, string destinationAddress, string symbol, uint256 amount)`

## `ContractCall(address sender, string destinationChain, string destinationContractAddress, bytes32 payloadHash, bytes payload)`

## `ContractCallWithToken(address sender, string destinationChain, string destinationContractAddress, bytes32 payloadHash, bytes payload, string symbol, uint256 amount)`

## `Executed(bytes32 commandId)`

## `TokenDeployed(string symbol, address tokenAddresses)`

## `ContractCallApproved(bytes32 commandId, string sourceChain, string sourceAddress, address contractAddress, bytes32 payloadHash, bytes32 sourceTxHash, uint256 sourceEventIndex)`

## `ContractCallApprovedWithMint(bytes32 commandId, string sourceChain, string sourceAddress, address contractAddress, bytes32 payloadHash, string symbol, uint256 amount, bytes32 sourceTxHash, uint256 sourceEventIndex)`

## `TokenMintLimitUpdated(string symbol, uint256 limit)`

## `OperatorshipTransferred(bytes newOperatorsData)`

## `Upgraded(address implementation)`
