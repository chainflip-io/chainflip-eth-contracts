# `Vault`

  The vault for holding and transferring native/tokens and deploying contracts for fetching
          individual deposits. It also allows users to do cross-chain swaps and(or) calls by
          making a function call directly to this contract.

## `timeoutEmergency()`

   Check that no nonce has been consumed in the last 14 days - emergency

## `constructor(contract IKeyManager keyManager)` (public)

No description

## `_getGovernor() → address` (internal)

No description

## `_getCommunityKey() → address` (internal)

No description

## `allBatch(struct IShared.SigData sigData, struct IShared.DeployFetchParams[] deployFetchParamsArray, struct IShared.FetchParams[] fetchParamsArray, struct IShared.TransferParams[] transferParamsArray)` (external)

 Can do a combination of all fcns in this contract. It first fetches all
         deposits , then it performs all transfers specified with the rest
         of the inputs, the same as transferBatch (where all inputs are again required
         to be of equal length - however the lengths of the fetch inputs do not have to
         be equal to lengths of the transfer inputs). Fetches/transfers of native are
         indicated with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address.

- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `deployFetchParamsArray`:    The array of deploy and fetch parameters

- `fetchParamsArray`:    The array of fetch parameters

- `transferParamsArray`: The array of transfer parameters

## `transfer(struct IShared.SigData sigData, struct IShared.TransferParams transferParams)` (external)

 Transfers native or a token from this vault to a recipient

- `sigData`:   The keccak256 hash over the msg (uint) (here that's
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `transferParams`:       The transfer parameters

## `transferBatch(struct IShared.SigData sigData, struct IShared.TransferParams[] transferParamsArray)` (external)

 Transfers native or tokens from this vault to recipients.

- `sigData`:   The keccak256 hash over the msg (uint) (here that's a hash over
                 the calldata to the function with an empty sigData) and sig over
                 that hash (uint) from the aggregate key

- `transferParamsArray`: The array of transfer parameters.

## `deployAndFetchBatch(struct IShared.SigData sigData, struct IShared.DeployFetchParams[] deployFetchParamsArray)` (external)

 Retrieves any token from multiple address, deterministically generated using
         create2, by creating a contract for that address, sending it to this vault.

- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `deployFetchParamsArray`:    The array of deploy and fetch parameters

## `fetchBatch(struct IShared.SigData sigData, struct IShared.FetchParams[] fetchParamsArray)` (external)

 Retrieves any token addresses where a Deposit contract is already deployed.

- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `fetchParamsArray`:    The array of fetch parameters

## `xSwapNative(uint32 dstChain, bytes dstAddress, uint16 dstToken)` (external)

 Swaps native token for a token in another chain. The egress token will be transferred to the specified
         destination address on the destination chain.

- `dstChain`:      The destination chain according to the Chainflip Protocol's nomenclature.

- `dstAddress`:    Bytes containing the destination address on the destination chain.

- `dstToken`:      Destination token to be swapped to.

## `xSwapToken(uint32 dstChain, bytes dstAddress, uint16 dstToken, contract IERC20 srcToken, uint256 amount)` (external)

 Swaps ERC20 token for a token in another chain. The desired token will be transferred to the specified
         destination address on the destination chain. The provided ERC20 token must be supported by the Chainflip Protocol.

- `dstChain`:      The destination chain according to the Chainflip Protocol's nomenclature.

- `dstAddress`:    Bytes containing the destination address on the destination chain.

- `dstToken`:      Uint containing the specifics of the swap to be performed according to Chainflip's nomenclature.

- `srcToken`:      Address of the source token to swap.

- `amount`:        Amount of tokens to swap.

## `xCallNative(uint32 dstChain, bytes dstAddress, uint16 dstToken, bytes message, uint256 gasAmount, bytes refundAddress)` (external)

 Performs a cross-chain call to the destination address on the destination chain. Native tokens must be paid
         to this contract. The swap intent determines if the provided tokens should be swapped to a different token
         and transferred as part of the cross-chain call. Otherwise, all tokens are used as a payment for gas on the destination chain.
         The message parameter is transmitted to the destination chain as part of the cross-chain call.

- `dstChain`:      The destination chain according to the Chainflip Protocol's nomenclature.

- `dstAddress`:    Bytes containing the destination address on the destination chain.

- `dstToken`:      Uint containing the specifics of the swap to be performed, if any, as part of the xCall. The string
                     must follow Chainflip's nomenclature. It can signal that no swap needs to take place
                     and the source token will be used for gas in a swapless xCall.

- `message`:       The message to be sent to the egress chain. This is a general purpose message.

- `gasAmount`:  The amount of native gas to be used on the destination chain's call.

- `refundAddress`: Address for any future refunds to the user.

## `xCallToken(uint32 dstChain, bytes dstAddress, uint16 dstToken, bytes message, uint256 gasAmount, contract IERC20 srcToken, uint256 amount, bytes refundAddress)` (external)

 Performs a cross-chain call to the destination chain and destination address. An ERC20 token amount
         needs to be approved to this contract. The ERC20 token must be supported by the Chainflip Protocol.
         The swap intent determines whether the provided tokens should be swapped to a different token
         by the Chainflip Protocol. If so, the swapped tokens will be transferred to the destination chain as part
         of the cross-chain call. Otherwise, the tokens are used as a payment for gas on the destination chain.
         The message parameter is transmitted to the destination chain as part of the cross-chain call.

- `dstChain`:      The destination chain according to the Chainflip Protocol's nomenclature.

- `dstAddress`:    Bytes containing the destination address on the destination chain.

- `dstToken`:      Uint containing the specifics of the swap to be performed, if any, as part of the xCall. The string
                     must follow Chainflip's nomenclature. It can signal that no swap needs to take place
                     and the source token will be used for gas in a swapless xCall.

- `message`:       The message to be sent to the egress chain. This is a general purpose message.

- `gasAmount`:  The amount of native gas to be used on the destination chain's call. That gas will be paid with the
                     source token.

- `srcToken`:      Address of the source token.

- `amount`:        Amount of tokens to swap.

- `refundAddress`: Address for any future refunds to the user.

## `addGasNative(bytes32 swapID)` (external)

 Add gas (topup) to an existing cross-chain call with the unique identifier swapID.
         Native tokens must be paid to this contract as part of the call.

- `swapID`:    The unique identifier for this swap (bytes32)

## `addGasToken(bytes32 swapID, uint256 amount, contract IERC20 token)` (external)

 Add gas (topup) to an existing cross-chain call with the unique identifier swapID.
         A Chainflip supported token must be paid to this contract as part of the call.

- `swapID`:    The unique identifier for this swap (bytes32)

- `token`:     Address of the token to provide.

- `amount`:    Amount of tokens to provide.

## `executexSwapAndCall(struct IShared.SigData sigData, struct IShared.TransferParams transferParams, uint32 srcChain, bytes srcAddress, bytes message)` (external)

 Transfers ETH or a token from this vault to a recipient and makes a function call
         completing a cross-chain swap and call. The ICFReceiver interface is expected on
         the receiver's address. A message is passed to the receiver along with other
         parameters specifying the origin of the swap.

- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally a hash over
                 the calldata to the function with an empty sigData) and sig over that
                 that hash (uint) from the aggregate key.

- `transferParams`:  The transfer parameters

- `srcChain`:        The source chain where the call originated from.

- `srcAddress`:      The address where the transfer originated within the ingress chain.

- `message`:         The message to be passed to the recipient.

## `executexCall(struct IShared.SigData sigData, address recipient, uint32 srcChain, bytes srcAddress, bytes message)` (external)

 Executes a cross-chain function call. The ICFReceiver interface is expected on
         the receiver's address. A message is passed to the receiver along with other
         parameters specifying the origin of the swap. This is used for cross-chain messaging
         without any swap taking place on the Chainflip Protocol.

- `sigData`:   The keccak256 hash over the msg (uint) (here that's normally
                 a hash over the calldata to the function with an empty sigData) and
                 sig over that hash (uint) from the aggregate key

- `srcChain`:       The source chain where the call originated from.

- `srcAddress`:     The address where the transfer originated from in the ingressParams.

- `message`:        The message to be passed to the recipient.

## `govWithdraw(address[] tokens)` (external)

Withdraw all funds to governance address in case of emergency. This withdrawal needs
        to be approved by the Community and it can only be executed if no nonce from the
        current AggKey had been consumed in _AGG_KEY_TIMEOUT time. It is a last resort and
        can be used to rectify an emergency.

- `tokens`:    The addresses of the tokens to be transferred

## `receive()` (external)

No description

## `TransferNativeFailed(address payable recipient, uint256 amount)`

## `TransferTokenFailed(address payable recipient, uint256 amount, address token, bytes reason)`

## `SwapNative(uint32 dstChain, bytes dstAddress, uint16 dstToken, uint256 amount, address sender)`

## `SwapToken(uint32 dstChain, bytes dstAddress, uint16 dstToken, address srcToken, uint256 amount, address sender)`

## `XCallNative(uint32 dstChain, bytes dstAddress, uint16 dstToken, uint256 amount, address sender, bytes message, uint256 gasAmount, bytes refundAddress)`

dstAddress is not indexed because indexing a dynamic type (string) to be able to filter,
     makes it so we won't be able to decode it unless we specifically search for it. If we want
     to filter it and decode it then we would need to have both the indexed and the non-indexed
     version in the event.

## `XCallToken(uint32 dstChain, bytes dstAddress, uint16 dstToken, address srcToken, uint256 amount, address sender, bytes message, uint256 gasAmount, bytes refundAddress)`

## `AddGasNative(bytes32 swapID, uint256 amount)`

## `AddGasToken(bytes32 swapID, uint256 amount, address token)`
