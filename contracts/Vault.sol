pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./interfaces/IVault.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IERC20Lite.sol";
import "./interfaces/ICFReceiver.sol";
import "./abstract/Shared.sol";
import "./DepositEth.sol";
import "./DepositToken.sol";
import "./AggKeyNonceConsumer.sol";
import "./GovernanceCommunityGuarded.sol";

/**
 * @title    Vault contract
 * @notice   The vault for holding ETH/tokens and deploying contracts
 *           for fetching individual deposits
 */
contract Vault is IVault, AggKeyNonceConsumer, GovernanceCommunityGuarded {
    using SafeERC20 for IERC20;

    uint256 private constant _AGG_KEY_EMERGENCY_TIMEOUT = 14 days;

    event TransferFailed(address payable indexed recipient, uint256 amount, bytes lowLevelData);

    // We don't index the dstAddress because it's a string (dynamicType). If we index it to be able to filter,
    // then unless we specically search for it we won't be able to decode it.
    // See: https://ethereum.stackexchange.com/questions/6840/indexed-event-with-string-not-getting-logged
    event XCallNative(
        uint32 dstChain,
        string dstAddress,
        string swapIntent,
        uint256 amount,
        address indexed sender,
        bytes message,
        address refundAddress
    );
    event XCallToken(
        uint32 dstChain,
        string dstAddress,
        string swapIntent,
        address srcToken,
        uint256 amount,
        address indexed sender,
        bytes message,
        address refundAddress
    );
    event SwapNative(uint32 dstChain, string dstAddress, string swapIntent, uint256 amount, address indexed sender);
    event SwapToken(
        uint32 dstChain,
        string dstAddress,
        string swapIntent,
        address srcToken,
        uint256 amount,
        address indexed sender
    );
    event AddNativeGas(bytes32 swapID, uint256 amount);
    event AddGas(bytes32 swapID, address token, uint256 amount);

    event XCallsEnabled(bool enabled);

    bool private _xCallsEnabled;

    constructor(IKeyManager keyManager) AggKeyNonceConsumer(keyManager) {}

    /// @dev   Get the governor address from the KeyManager. This is called by the onlyGovernor
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getGovernor() internal view override returns (address) {
        return getKeyManager().getGovernanceKey();
    }

    /// @dev   Get the community key from the KeyManager. This is called by the isCommunityKey
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getCommunityKey() internal view override returns (address) {
        return getKeyManager().getCommunityKey();
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Transfer and Fetch                      //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Can do a combination of all fcns in this contract. It first fetches all
     *          deposits specified with fetchSwapIDs and fetchTokens (which are requried
     *          to be of equal length), then it performs all transfers specified with the rest
     *          of the inputs, the same as transferBatch (where all inputs are again required
     *          to be of equal length - however the lengths of the fetch inputs do not have to
     *          be equal to lengths of the transfer inputs). Fetches/transfers of ETH are indicated
     *          with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param fetchParamsArray    The array of fetch parameters
     * @param transferParamsArray The array of transfer parameters
     */
    function allBatch(
        SigData calldata sigData,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    )
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.allBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    fetchParamsArray,
                    transferParamsArray
                )
            )
        )
    {
        // Fetch all deposits
        _fetchBatch(fetchParamsArray);

        // Send all transfers
        _transferBatch(transferParamsArray);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Transfers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Transfers ETH or a token from this vault to a recipient
     * @param sigData   The keccak256 hash over the msg (uint) (here that's
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param transferParams       The transfer parameters
     */
    function transfer(SigData calldata sigData, TransferParams calldata transferParams)
        external
        override
        onlyNotSuspended
        nzAddr(address(transferParams.token))
        nzAddr(transferParams.recipient)
        nzUint(transferParams.amount)
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.transfer.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    transferParams
                )
            )
        )
    {
        _transfer(transferParams.token, transferParams.recipient, transferParams.amount);
    }

    /**
     * @notice  Transfers ETH or tokens from this vault to recipients.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param transferParamsArray The array of transfer parameters.
     */
    function transferBatch(SigData calldata sigData, TransferParams[] calldata transferParamsArray)
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.transferBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    transferParamsArray
                )
            )
        )
    {
        _transferBatch(transferParamsArray);
    }

    /**
     * @notice  Transfers ETH or tokens from this vault to recipients.
     * @param transferParamsArray The array of transfer parameters.
     */
    function _transferBatch(TransferParams[] calldata transferParamsArray) private {
        uint256 length = transferParamsArray.length;
        for (uint256 i = 0; i < length; ) {
            _transfer(transferParamsArray[i].token, transferParamsArray[i].recipient, transferParamsArray[i].amount);
            unchecked {
                ++i;
            }
        }
    }

    /**
     * @notice  Annoyingly, doing `try addr.transfer` in `_transfer` fails because
     *          Solidity doesn't see the `address` type as an external contract
     *          and so doing try/catch on it won't work. Need to make it an external
     *          call, and doing `this.something` counts as an external call, but that
     *          means we need a fcn that just sends eth
     * @param recipient The address to receive the ETH
     */
    function sendEth(address payable recipient) external payable {
        require(msg.sender == address(this), "Vault: only Vault can send ETH");
        recipient.transfer(msg.value);
    }

    /**
     * @notice  Transfers ETH or a token from this vault to a recipient
     * @param token The address of the token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei (uint)
     */
    function _transfer(
        address token,
        address payable recipient,
        uint256 amount
    ) private {
        if (token == _ETH_ADDR) {
            try this.sendEth{value: amount}(recipient) {} catch (bytes memory lowLevelData) {
                emit TransferFailed(recipient, amount, lowLevelData);
            }
        } else {
            IERC20(token).safeTransfer(recipient, amount);
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Fetch Deposits                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Retrieves ETH and tokens from multiple addresses, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param fetchParamsArray    The array of fetch parameters
     */
    function _fetchBatch(FetchParams[] calldata fetchParamsArray) private {
        // Fetch all deposits
        uint256 length = fetchParamsArray.length;
        for (uint256 i = 0; i < length; ) {
            if (address(fetchParamsArray[i].token) == _ETH_ADDR) {
                new DepositEth{salt: fetchParamsArray[i].swapID}();
            } else {
                new DepositToken{salt: fetchParamsArray[i].swapID}(IERC20Lite(fetchParamsArray[i].token));
            }
            unchecked {
                ++i;
            }
        }
    }

    /**
     * @notice  Retrieves ETH from an address, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param swapID    The unique identifier for this swap (bytes32)
     */
    function fetchDepositEth(SigData calldata sigData, bytes32 swapID)
        external
        override
        onlyNotSuspended
        nzBytes32(swapID)
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetchDepositEth.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    swapID
                )
            )
        )
    {
        new DepositEth{salt: swapID}();
    }

    /**
     * @notice  Retrieves ETH from multiple addresses, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param swapIDs    The unique identifiers for this swap (bytes32)
     */
    function fetchDepositEthBatch(SigData calldata sigData, bytes32[] calldata swapIDs)
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetchDepositEthBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    swapIDs
                )
            )
        )
    {
        uint256 length = swapIDs.length;
        for (uint256 i; i < length; ) {
            new DepositEth{salt: swapIDs[i]}();
            unchecked {
                ++i;
            }
        }
    }

    /**
     * @notice  Retrieves a token from an address deterministically generated using
     *          create2 by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param fetchParams    The fetch parameters
     */
    function fetchDepositToken(SigData calldata sigData, FetchParams calldata fetchParams)
        external
        override
        onlyNotSuspended
        nzBytes32(fetchParams.swapID)
        nzAddr(address(fetchParams.token))
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetchDepositToken.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    fetchParams
                )
            )
        )
    {
        new DepositToken{salt: fetchParams.swapID}(IERC20Lite(fetchParams.token));
    }

    /**
     * @notice  Retrieves tokens from multiple addresses, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param fetchParamsArray    The array of fetch parameters
     */
    function fetchDepositTokenBatch(SigData calldata sigData, FetchParams[] calldata fetchParamsArray)
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetchDepositTokenBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    fetchParamsArray
                )
            )
        )
    {
        uint256 length = fetchParamsArray.length;
        for (uint256 i; i < length; ) {
            new DepositToken{salt: fetchParamsArray[i].swapID}(IERC20Lite(address(fetchParamsArray[i].token)));
            unchecked {
                ++i;
            }
        }
    }

    ///NOTE: Thorchain has only ONE string, idea being that it can be used for swapping and for adding liquidity!
    ///      They do it because in the context of providing liquidity, the dstAddress doesn't make sense.
    ///      FUNCTION:PARAM1:PARAM2:PARAM3:PARAM4
    ///      In our case reusing this function is not great anyway (due to message and refundAddress paramts). Also, for any other chain
    ///      the ingressAddress method will be used, so having a function to provide liquidity doesn't seem particularly useful.

    // TODO: if we refund we need to add a refund address. For example, if LiFi is in the middle, we want to refund the user, not LiFi.
    //       This is the case if we do a retrospective refund.
    // TODO: If we want to allow gas topups then a txHash parameter should be use as an input to match with the transaction. This way
    //       there wouldn't be a need to add a transferID at the smart contract level. Since the monitoring needs to be done off-chain
    //       anyway, I would suggest to use the swapID that CF will create to track swaps.
    // TODO: We could also consider issuing the refunds on the egress chains to a passed string (instead of an address like now).
    //       That logic can also apply to the gas top-up, it could be done also on the egressChain-

    // TODO: To think what gating (xCallsEnabled) we want to have if any, since that costs gas (sload).
    // TODO: Think if we want to have the EVM-versions of the ingress functions since converting address to string is very expensive
    //       gas-wise, for example using OZ's Strings library.
    // TODO: Lifi for some reason constructs the strings and message on-chain e.g. converting EVM address to string on-chain by using
    //       OZ's string library. That is a huge waste of gas, instead of passing the address as a string directly. Why do they do
    //       that? Seems like they are still not live with Axelar, so it might still be under development, since that doesn't make sense.
    //       Maybe they have it to allow a direct swap to Axelar but it's still not integrated properly into the LiFi backend.
    // TODO: Depending on LiFi (and also on us) we can explore having just one long string (like ThorChain memo). Better gas and
    //       flexibility. Also, concatenation on the ingress is easy and not too expensive. Problem is that it is not very intuitive,
    //       it makes it cumbersome to build it on-chain (if the whole string is not passed as calldata). Also, on the dstChain it is
    //       a pain to check srcChain as a string.
    // TODO: Seems like we want to support Pure CCM. For now we do that by calling the xCallToken but passing an emtpy swapIntent.
    //       If we want to optimize pure CCM then we could create two extra functions (paying with native or with token).

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                    SrcChain xSwap                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Performs a cross-chain swap. Native tokens provided are swapped by the Chainflip Protocol for the 
     *          token specified in the swap intent. The desired token will be transferred to the specified destination
     *          address on the destination chain.
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity indicate that an amount is required.  It isn't preventing spamming.

     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    String containing the destination address on the destination chain.
     * @param swapIntent    String containing the specifics of the swap to be performed according to Chainflip's nomenclature.
     */
    function xSwapNative(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent
    ) external payable override onlyNotSuspended nzUint(msg.value) {
        emit SwapNative(dstChain, dstAddress, swapIntent, msg.value, msg.sender);
    }

    /**
     * @notice  Performs a cross-chain swap. The ERC20 token provided is swapped by the Chainflip Protocol for the 
     *          token specified in the swap intent. The desired token will be transferred to the specified destination
     *          address on the destination chain. The ERC20 token must be supported by the Chainflip Protocol. 
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity indicate that an amount is required.

     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    String containing the destination address on the destination chain.
     * @param swapIntent    String containing the specifics of the swap to be performed according to Chainflip's nomenclature.
     * @param srcToken      Address of the token to swap.
     * @param amount        Amount of tokens to swap.
     */
    function xSwapToken(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        IERC20 srcToken,
        uint256 amount
    ) external override onlyNotSuspended nzUint(amount) {
        srcToken.safeTransferFrom(msg.sender, address(this), amount);
        emit SwapToken(dstChain, dstAddress, swapIntent, address(srcToken), amount, msg.sender);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                     SrcChain xCall                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Performs a cross-chain call to the destination chain and destination address. Native tokens must be paid 
     *          to this contract. The swap intent determines whether the provided tokens should be swapped to a different token
     *          by the Chainflip Protocol. If so, the swapped tokens will be transferred to the destination chain as part
     *          of the cross-chain call. Otherwise, the tokens are used as a payment for gas on the destination chain.
     *          The message parameter is transmitted to the destination chain as part of the cross-chain call.
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity inidcate that an amount is required. It isn't preventing spamming.
     *
     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    String containing the destination address on the destination chain.
     * @param swapIntent    String containing the specifics of the swap to be performed, if any, as part of the xCall. The string
     *                      must follow Chainflip's nomenclature. An empty swapIntent implies that no swap needs to take place
     *                      and the source token will be used for gas in a swapless xCall.
     * @param message       The message to be sent to the egress chain. This is a general purpose message.
     * @param refundAddress Address to refund any excess gas left from the execution of the xCall on the dstChain. This address
     *                      is in the context of the srcChain.
     */
    function xCallNative(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        address refundAddress
    ) external payable override onlyNotSuspended xCallsEnabled nzUint(msg.value) {
        emit XCallNative(dstChain, dstAddress, swapIntent, msg.value, msg.sender, message, refundAddress);
    }

    /**
     * @notice  Performs a cross-chain call to the destination chain and destination address. An ERC20 token amount
     *          needs to be approved to this contract. The ERC20 token must be supported by the Chainflip Protocol.
     *          The swap intent determines whether the provided tokens should be swapped to a different token
     *          by the Chainflip Protocol. If so, the swapped tokens will be transferred to the destination chain as part
     *          of the cross-chain call. Otherwise, the tokens are used as a payment for gas on the destination chain.
     *          The message parameter is transmitted to the destination chain as part of the cross-chain call.
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity indicate that an amount is required.
     *
     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    String containing the destination address on the destination chain.
     * @param swapIntent    String containing the specifics of the swap to be performed as part of the xCall. An empty swapIntent
     *                       implies that no swap needs to take place and the source token will be used for gas in a swapless xCall.
     * @param message       The message to be sent to the egress chain. This is a general purpose message.
     * @param srcToken      Address of the token to swap.
     * @param amount        Amount of tokens to swap.
     * @param refundAddress Address to refund any excess gas left from the execution of the xCall on the dstChain. This address
     *                      is in the context of the srcChain.
     */
    function xCallToken(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        IERC20 srcToken,
        uint256 amount,
        address refundAddress
    ) external override onlyNotSuspended xCallsEnabled nzUint(amount) {
        srcToken.safeTransferFrom(msg.sender, address(this), amount);
        emit XCallToken(
            dstChain,
            dstAddress,
            swapIntent,
            address(srcToken),
            amount,
            msg.sender,
            message,
            refundAddress
        );
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //             DstChain receive xSwap and call              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Transfers ETH or a token from this vault to a recipient and calls the receive
     *          function on the recipient's contract passing the message specified in the ingress
     *          chain among other parameters that specify the source and parameters of the transfer.
     *          This is used for swaps with cross-chain messaging. Can also be user for xswapWithCall
     *          even if the message is empty.
     * @dev     Could consider the amount and tokenAddress check to save some gas.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param transferParams  The transfer parameters
     * @param srcChain        The source chain where the call originated from.
     * @param srcAddress      The address where the transfer originated within the ingress chain.
     * @param message         The message to be passed to the recipient.
     */
    function executexSwapAndCall(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    )
        external
        override
        onlyNotSuspended
        nzAddr(transferParams.token)
        nzAddr(transferParams.recipient)
        nzUint(transferParams.amount)
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.executexSwapAndCall.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    transferParams,
                    srcChain,
                    srcAddress,
                    message
                )
            )
        )
    {
        // Making an extra call to gain some stack room (avoid stackTooDeep error)
        _executexSwapAndCall(transferParams, srcChain, srcAddress, message);
    }

    function _executexSwapAndCall(
        TransferParams calldata transferParams,
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) private {
        // NOTE: It's on the receiver to make sure this call doesn't revert so they keep the tokens.
        // This is done espeically for integrations with protocols (such as  LiFi) where we don't know the
        // user/final address, so if we just transfer to the recipient in case of a revert, we might end up
        // with tokens locked up in a DEX aggregator. Better to let it handle by the DEX or by the user's
        // smart contract for more flexibility. Also because we allow them to replay it if they want to.
        // NOTE: Seems like both LiFi and RangoExchange have the try-catch on their side to handle exactly
        // this, so it seems like the best approach.
        // NOTE: We don't use the _transfer function because we want to be able to embed the native token
        // into the cfReceive call to avoid a double cross-contract call.

        if (transferParams.token == _ETH_ADDR) {
            ICFReceiver(transferParams.recipient).cfRecieve{value: transferParams.amount}(
                srcChain,
                srcAddress,
                message,
                transferParams.token,
                transferParams.amount
            );
        } else {
            IERC20(transferParams.token).safeTransfer(transferParams.recipient, transferParams.amount);
            ICFReceiver(transferParams.recipient).cfRecieve(
                srcChain,
                srcAddress,
                message,
                transferParams.token,
                transferParams.amount
            );
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                   DstChain receive xcall                 //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Calls the receive function on the recipient's contract passing the message specified
     *          and the source of the call (ingress)
     *          This is used for pure cross-chain messaging.
     * @dev     We might not support this straight-away since we are focused on cross-chain swaps.
     * @dev     ingressParams and srcAddress are separated to make it easier for the recipient to
     *          do any checks without needing to split a string. IngressParams as of now it would only
     *          be srcChain (no need for srcToken) but leaving it general in case we need it.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param srcChain       The source chain where the call originated from.
     * @param srcAddress     The address where the transfer originated from in the ingressParams.
     * @param message        The message to be passed to the recipient.
     */
    function executexCall(
        SigData calldata sigData,
        address recipient,
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    )
        external
        override
        onlyNotSuspended
        nzAddr(recipient)
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.executexCall.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    recipient,
                    srcChain,
                    srcAddress,
                    message
                )
            )
        )
    {
        ICFReceiver(recipient).cfRecievexCall(srcChain, srcAddress, message);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                     Gas topup                            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    // TODO: To decide if we want this for the future or not. Native gas would be great to offer
    // gas topups on the egress chain. But non-native would be good because USDC is easier to
    // handle/swap internally.
    // Potentially we could use this two functions to allow the user to cancel an egress
    // transaction. This could be done by sending zero amount and signaling the swapID.
    // NOTE: This could be features for later on, and together with the refundAddress it might
    // be worth removing and maybe adding in the future.
    // TODO: To verify this if we decide to have it.

    function addNativeGas(bytes32 swapID) external payable xCallsEnabled {
        emit AddNativeGas(swapID, msg.value);
    }

    function addGas(
        bytes32 swapID,
        IERC20 token,
        uint256 amount
    ) external nzUint(amount) xCallsEnabled {
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        emit AddGas(swapID, address(token), amount);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Governance                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice Withdraw all funds to governance address in case of emergency. This withdrawal needs
     *         to be approved by the Community and it can only be executed if no nonce from the
     *         current AggKey had been consumed in _AGG_KEY_TIMEOUT time. It is a last resort and
     *         can be used to rectify an emergency.
     * @param tokens    The addresses of the tokens to be transferred
     */
    function govWithdraw(address[] calldata tokens)
        external
        override
        onlyGovernor
        onlyCommunityGuardDisabled
        onlySuspended
        timeoutEmergency
    {
        // Could use msg.sender or getGovernor() but hardcoding the get call just for extra safety
        address payable recipient = payable(getKeyManager().getGovernanceKey());

        // Transfer all ETH and ERC20 Tokens
        for (uint256 i = 0; i < tokens.length; i++) {
            if (address(tokens[i]) == _ETH_ADDR) {
                _transfer(_ETH_ADDR, recipient, address(this).balance);
            } else {
                _transfer(tokens[i], recipient, IERC20(tokens[i]).balanceOf(address(this)));
            }
        }
    }

    /**
     * @notice  Enable swapETH and swapToken functionality by governance. Features disabled by default
     */
    function enablexCalls() external override onlyGovernor xCallsDisabled {
        _xCallsEnabled = true;
        emit XCallsEnabled(true);
    }

    /**
     * @notice  Disable swapETH and swapToken functionality by governance. Features disabled by default.
     */
    function disablexCalls() external override onlyGovernor xCallsEnabled {
        _xCallsEnabled = false;
        emit XCallsEnabled(false);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get xCallsEnabled
     * @return  The xCallsEnableds state
     */
    function getxCallsEnabled() external view override returns (bool) {
        return _xCallsEnabled;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that no nonce of the current AggKey has been consumed in the last 14 days - emergency
    modifier timeoutEmergency() {
        require(
            block.timestamp - getKeyManager().getLastValidateTime() >= _AGG_KEY_EMERGENCY_TIMEOUT,
            "Vault: not enough time"
        );
        _;
    }

    /// @dev    Check that xCalls are enabled
    modifier xCallsEnabled() {
        require(_xCallsEnabled, "Vault: xCalls not enabled");
        _;
    }

    /// @dev    Check that xCalls are disabled
    modifier xCallsDisabled() {
        require(!_xCallsEnabled, "Vault: xCalls enabled");
        _;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Fallbacks                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev For receiving ETH when fetchDepositEth is called
    receive() external payable {}
}
