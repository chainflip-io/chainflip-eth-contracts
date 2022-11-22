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
    event SwapNativeAndCall(
        uint32 dstChain,
        string dstAddress,
        string swapIntent,
        uint256 amount,
        address indexed sender,
        bytes message,
        address refundAddress
    );
    event SwapTokenAndCall(
        uint32 dstChain,
        string dstAddress,
        string swapIntent,
        address ingressToken,
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
        address ingressToken,
        uint256 amount,
        address indexed sender
    );
    event AddNativeGas(bytes32 swapID, uint256 amount);
    event AddGas(bytes32 swapID, address token, uint256 amount);

    event SwapsEnabled(bool enabled);

    bool private _swapsEnabled;

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
     *          with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address. It is assumed
     *          that the elements of each array match in terms of ordering, i.e. a given
     *          fetch should should have the same index swapIDs[i] and tokens[i]
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
     * @notice  Transfers ETH or tokens from this vault to recipients. It is assumed
     *          that the elements of each array match in terms of ordering, i.e. a given
     *          transfer should should have the same index tokens[i], recipients[i],
     *          and amounts[i].
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
     * @notice  Transfers ETH or tokens from this vault to recipients. It is assumed
     *          that the elements of each array match in terms of ordering, i.e. a given
     *          transfer should should have the same index tokens[i], recipients[i],
     *          and amounts[i].
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

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  SrcChain xSwap and call                  //
    //                                                          //
    //////////////////////////////////////////////////////////////

    ///NOTE: Thorchain has only ONE string, idea being that it can be used for swapping and for adding liquidity!
    ///      They do it because in the context of providing liquidity, the dstAddress doesn't make sense.
    ///      FUNCTION:PARAM1:PARAM2:PARAM3:PARAM4
    ///      In our case reusing this function is not great anyway (due to message and refundAddress paramts)
    ///      but we could consider having a separate function for adding liquidity.
    ///TODO: Should we have a separate function for adding liquidity? Or we will do it through the srcAddress method?

    // TODO: if we refund we need to add a refund address. For example, if LiFi is in the middle, we want to refund the user, not LiFi.
    //       This is the case if we do a retrospective refund. I would not try to glump xswapTokenWithCall and xswapToken even if only
    //       the message parameter differs to have different functions - makes it easier to signal if it's swap+CCM, only CCM or only swap.
    //       We could glump them all into one (empty message = no CCM, no egressToken == noSwap) but it seems clearer to keep it separate.
    //       Also because with DEX Aggregation we might want only a pre-swap, no postSwap and then setting empty messages is a waste of
    //       gas. Better have two separate functions if we can afford it (bytecodesize-wise). We effectively make an only-swap cheaper,
    //       which might be a very common use, especially when egressing to non-smart contract chains or for native egress tokens.
    //       These are the two main cases where we offer a lot of value to the users, so it makes sense to optimize.
    // TODO: If we want to allow gas topups then a txHash parameter should be use as an input to match with the transaction. This way
    //       there wouldn't be a need to add a transferID at the smart contract level. Since the monitoring needs to be done off-chain
    //       anyway, I would suggest to use the swapID that CF will create to track swaps.
    // TODO: Do we prefer uint for egressChain and egress token or a single string? Gaswise the uints are just a bit cheaper (not too
    //       relevant). Uints would be great for the egress part, since we only pass egress chain there. However, strings are useful to
    //       pass extra parameters in the future (similar to ThorChain's Memos)
    // TODO: Think if we want to have the EVM-versions of the ingress functions since converting address to string is super painful.
    // TODO: We could also consider issuing the refunds on the egress chains to a passed string (instead of an address like now).
    // TODO: To think what gating (swapsEnabled) we want to have if any, since that costs gas (sload).

    // NOTE: Used for swap+CCM and also for pure CCM (by having an empty egressToken)
    // NOTE: SwapIntent is for now equal to dstToken, but the name is more generic for the future. Does that make sense?

    /**
     * @notice  Swaps ERC20 Token for a token in another chain and performs a xcall. Function call needs to specify the src and
     *          destinatiopn parameters. It also has a cross-chain message capability. If no xcall is needed then xSwapToken should
     *          be used. If xcall is needed but no message is needed then the message field can be left empty.
     *          An empty dstToken (in swapIntent) signifies that only CCM is to be performed and the source Token shall be used for gas.
     * @dev     At the moment we are not prioritizing pure ccm. If we want to do so, we could create a separate function without swapIntent.
     * @dev     The check for existing parameters shall be done in the CFE. Checking non-empty string (swapIntent/dstAddress) is
     *          a bit of a waste of gas also because a non-empty string doesn't mean it's a valid dstAddress anyway.
     * @dev     dstChain and swapIntent (and even dstAddress) could be bundled together in a single string to shave a few hundred gas.
     *          However, dstChain is nicer as a uint for the egress calls so it can be checked easily, since checking string is terrible.
     *          Then, we could be including dstAddress inside swapIntent. I have kept it separate since swapIntent will most likely come
     *          from calldata while dstAddress might be a string stored in another protocols' smart contract. It is easy to concatenate
     *          via abi.encodePacked or via string.concat (0.8.12) so they could be bundled. But kept separately for now. TODO: Ponder?
     * @dev     Swapintent only being dstToken for now, but it allows for more parameters in the future.
     *
     * @param dstChain      The destination chain according to the Chainflip protocol's nomenclature.
     * @param dstAddress    String containing the egress address. An address type is not used since non-EVM chains don't follow this
     *                      format. A string is used (instead of bytes32) given that not all chains have a user-friendly way to
     *                      represent an address with bytes32.
     * @param swapIntent    String containing the desired destination Token and potentially in the future other parameters, e.g.
     *                      egressToken:MAXslippage:... If that is the case, when that is not coming from external call, it can
     *                      easily be concatenated after solidity 8.12 with string.concat(). Otherwise, with
     *                      string(abi.encodePacked(a,":",b)) as long as both a and b are stirings.
     *                      An empty egressToken signifies that only a CCM is performed and all ingress tokens are used for gas.
     *                      We can make a specific CCM without the swapIntent.
     * @param message       String containing the message to be sent to the egress chain. Can be empty if the user wants a xcall but
     *                      no message to be sent.
     * @param srcToken      Address of the token to swap.
     * @param amount        Amount of tokens to swap.
     * @param refundAddress Address to refund any excess gas. If we decide to refund on the egress, it would need to be a string.
     *                      We would still need an egress address, since for DEX aggregation dstAddress != userAddress.
     */
    function xSwapTokenAndCall(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        IERC20 srcToken,
        uint256 amount,
        address refundAddress
    ) external override onlyNotSuspended swapsEnabled nzUint(amount) {
        srcToken.safeTransferFrom(msg.sender, address(this), amount);
        emit SwapTokenAndCall(
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
    //                    SrcChain xSwap                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    // NOTE: Checking msg.value!=0 won't prevent spamming. However, it might be useful to ensure that users
    // understand that they should be paying gas. We check that in the token case because I have heard
    // people saying they have seen isssues when fuzzing transfering zero tokens.
    function xSwapNativeAndCall(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        address refundAddress
    ) external payable override onlyNotSuspended swapsEnabled nzUint(msg.value) {
        emit SwapNativeAndCall(dstChain, dstAddress, swapIntent, msg.value, msg.sender, message, refundAddress);
    }

    // NOTE: Used for swapOnly (also used in cross-chain aggregation when egressing to native asset or to non-smart
    // contract chain.
    /**
     * @dev     If we end up having a refundAddress on the send functions, then we have two parameters that are
     *          useless for an onlySwap function (which can even come from LiFi). In that case, I would have these
     *          two separate functions for swap-only.
     *          No need to do that for a CCM only, since a payment needs ot be done anyway (so only egressToken shall be empty).
     */
    function xSwapToken(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        IERC20 ingressToken,
        uint256 amount
    ) external override onlyNotSuspended swapsEnabled nzUint(amount) {
        ingressToken.safeTransferFrom(msg.sender, address(this), amount);
        emit SwapToken(dstChain, dstAddress, swapIntent, address(ingressToken), amount, msg.sender);
    }

    // TODO: Checking msg.value!=0 won't prevent spamming, so we might consider removing it. It would only be
    // for users to understand that they should be paying an ingress native Token. We check that in the token
    // case because I have heard people saying they have seen isssues when fuzzing transfering zero tokens.
    function xSwapNative(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent
    ) external payable override onlyNotSuspended swapsEnabled nzUint(msg.value) {
        emit SwapNative(dstChain, dstAddress, swapIntent, msg.value, msg.sender);
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
     * @dev     srcChain and srcAddress are separated to make it easier for the recipient to
     *          do any checks without needing to split a string.
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
        // TODO: Originally we copied this parameters to avoid StackTooDeep error. But now that this function is
        // separate we might have a bit more of a buffer. To play a bit more with it since we are probably
        // spending a bit more gas by doing that. If we have to do this we can maybe just pass those as parameters
        // to the _egress function anyway.
        uint256 amount = transferParams.amount;
        address token = address(transferParams.token);
        address payable recipient = transferParams.recipient;

        // NOTE: It's on the receiver to make sure this call doesn't revert so they keep the tokens.
        // This is done espeically for integrations with protocols (such as  LiFi) where we don't know the
        // user/final address, so if we just transfer to the recipient in case of a revert, we might end up
        // with tokens locked up in a DEX aggregator. Better to let it handle by the DEX or by the user's
        // smart contract for more flexibility. Also because we allow them to replay it if they want to.
        // NOTE: Seems like both LiFi and RangoExchange have the try-catch on their side to handle exactly
        // this, so it seems like the best approach.
        // NOTE: We don't use the _transfer function because we want to be able to embed the native token
        // into the cfReceive call to avoid a double cross-contract call.

        if (token == _ETH_ADDR) {
            ICFReceiver(recipient).cfRecieve{value: amount}(srcChain, srcAddress, message, token, amount);
        } else {
            IERC20(token).safeTransfer(recipient, amount);
            ICFReceiver(recipient).cfRecieve(srcChain, srcAddress, message, token, amount);
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
     *          be srcChain (no need for ingressToken) but leaving it general in case we need it.
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

    // NOTE: To decide if we want this for the future or not. Native gas would be great to offer
    // gas topups on the egress chain. But non-native would be good because USDC is easier to
    // handle/swap internally.
    // Potentially we could use this two functions to allow the user to cancel an egress
    // transaction. This could be done by sending zero amount and signaling the swapID.
    // NOTE: This could be features for later on, and together with the refundAddress it might
    // be worth removing and maybe adding in the future.

    function addNativeGas(bytes32 swapID) external payable {
        emit AddNativeGas(swapID, msg.value);
    }

    function addGas(
        bytes32 swapID,
        IERC20 token,
        uint256 amount
    ) external nzUint(amount) {
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
    function enableSwaps() external override onlyGovernor swapsDisabled {
        _swapsEnabled = true;
        emit SwapsEnabled(true);
    }

    /**
     * @notice  Disable swapETH and swapToken functionality by governance. Features disabled by default.
     */
    function disableSwaps() external override onlyGovernor swapsEnabled {
        _swapsEnabled = false;
        emit SwapsEnabled(false);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get swapsEnabled
     * @return  The swapsEnableds state
     */
    function getSwapsEnabled() external view override returns (bool) {
        return _swapsEnabled;
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

    /// @dev    Check that swaps are enabled
    modifier swapsEnabled() {
        require(_swapsEnabled, "Vault: swaps not enabled");
        _;
    }

    /// @dev    Check that swaps are disabled
    modifier swapsDisabled() {
        require(!_swapsEnabled, "Vault: swaps enabled");
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
