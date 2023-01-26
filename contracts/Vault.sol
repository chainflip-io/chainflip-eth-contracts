pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./interfaces/IVault.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IERC20Lite.sol";
import "./interfaces/ICFReceiver.sol";
import "./abstract/Shared.sol";
import "./Deposit.sol";
import "./AggKeyNonceConsumer.sol";
import "./GovernanceCommunityGuarded.sol";

/**
 * @title    Vault contract
 * @notice   The vault for holding and transferring native/tokens and deploying contracts for fetching
 *           individual deposits. It also allows users to do cross-chain swaps and(or) calls by
 *           making a function call directly to this contract.
 */
contract Vault is IVault, AggKeyNonceConsumer, GovernanceCommunityGuarded {
    using SafeERC20 for IERC20;

    uint256 private constant _AGG_KEY_EMERGENCY_TIMEOUT = 14 days;
    uint256 private constant _GAS_TO_FORWARD = 3500;

    event TransferFailed(address payable indexed recipient, uint256 amount);
    event FetchFailed(address payable indexed fetchContract, address indexed token);
    event SwapNative(uint256 amount, string egressParams, bytes32 egressReceiver);
    event SwapToken(address ingressToken, uint256 amount, string egressParams, bytes32 egressReceiver);
    event SwapsEnabled(bool enabled);

    /// @dev dstAddress is not indexed because indexing a dynamic type (string) to be able to filter,
    ///      makes it so we won't be able to decode it unless we specifically search for it. If we want
    ///      to filter it and decode it then we would need to have both the indexed and the non-indexed
    ///      version in the event.
    event XCallNative(
        uint32 dstChain,
        string dstAddress,
        string swapIntent,
        uint256 amount,
        address indexed sender,
        bytes message,
        uint256 dstNativeGas,
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
        uint256 dstNativeGas,
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
     *          deposits , then it performs all transfers specified with the rest
     *          of the inputs, the same as transferBatch (where all inputs are again required
     *          to be of equal length - however the lengths of the fetch inputs do not have to
     *          be equal to lengths of the transfer inputs). Fetches/transfers of native are
     *          indicated with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param deployFetchParamsArray    The array of deploy and fetch parameters
     * @param fetchParamsArray    The array of fetch parameters
     * @param transferParamsArray The array of transfer parameters
     */
    function allBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
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
                    deployFetchParamsArray,
                    fetchParamsArray,
                    transferParamsArray
                )
            )
        )
    {
        // Fetch all deposits
        _fetchBatch(deployFetchParamsArray, fetchParamsArray);

        // Send all transfers
        _transferBatch(transferParamsArray);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Transfers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Transfers native or a token from this vault to a recipient
     * @param sigData   The keccak256 hash over the msg (uint) (here that's
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param transferParams       The transfer parameters
     */
    function transfer(SigData calldata sigData, TransferParams calldata transferParams)
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
     * @notice  Transfers native or tokens from this vault to recipients.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's a hash over
     *                  the calldata to the function with an empty sigData) and sig over
     *                  that hash (uint) from the aggregate key
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
     * @notice  Transfers native or tokens from this vault to recipients.
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
     * @notice  Transfers ETH or a token from this vault to a recipient
     * @dev     Using "send" function to only send a set amount of gas, preventing the recipient
     *          from using all the transfer batch gas. Also, not reverting on failure so it can't
     *          block the batch transfer.
     * @param token The address of the token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei (uint)
     */
    function _transfer(
        address token,
        address payable recipient,
        uint256 amount
    ) private {
        if (address(token) == _NATIVE_ADDR) {
            // Disable because we don't want to revert on failure. Forward only a set amount of gas
            // so the receivers can't consume all the gas.
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = recipient.call{gas: _GAS_TO_FORWARD, value: amount}("");
            if (!success) {
                emit TransferFailed(recipient, amount);
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
     * @notice  Retrieves tokens from multiple addresses. Either from a deterministically generated 
     *          address using create2, by creating a contract for that address and sending it to this vault,
     *          or by calling the fetch function of an already deployed Deposit contract.

     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param deployFetchParamsArray    The array of deploy and fetch parameters
     * @param fetchParamsArray          The array of fetch parameters
     */
    function fetchBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
        FetchParams[] calldata fetchParamsArray
    )
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetchBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    deployFetchParamsArray,
                    fetchParamsArray
                )
            )
        )
    {
        _fetchBatch(deployFetchParamsArray, fetchParamsArray);
    }

    /**
     * @notice  Retrieves tokens from multiple addresses. Either from a deterministically generated
     *          address using create2, by creating a contract for that address and sending them to this vault,
     *          or by calling the fetch function of an already deployed Deposit contract.
     * @dev     FetchAndDeploy is executed first to handle the edge case , which probably shouldn't
     *          happen anyway, where a deploy and a fetch for the same address are in the same batch.
     * @param deployFetchParamsArray    The array of deploy and fetch parameters
     * @param fetchParamsArray    The array of fetch parameters
     */
    function _fetchBatch(DeployFetchParams[] calldata deployFetchParamsArray, FetchParams[] calldata fetchParamsArray)
        private
    {
        // Deploy deposit contracts
        uint256 length = deployFetchParamsArray.length;
        uint256 i;
        for (i = 0; i < length; ) {
            new Deposit{salt: deployFetchParamsArray[i].swapID}(IERC20Lite(deployFetchParamsArray[i].token));
            unchecked {
                ++i;
            }
        }

        // Fetch from already deployed contracts
        length = fetchParamsArray.length;
        for (i = 0; i < length; ) {
            _fetch(fetchParamsArray[i]);
            unchecked {
                ++i;
            }
        }
    }

    /**
     * @notice  Retrieves any token from an address, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param deployFetchParams    The deploy and fetch parameters
     */
    function deployAndFetch(SigData calldata sigData, DeployFetchParams calldata deployFetchParams)
        external
        override
        onlyNotSuspended
        nzBytes32(deployFetchParams.swapID)
        nzAddr(address(deployFetchParams.token))
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.deployAndFetch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    deployFetchParams
                )
            )
        )
    {
        new Deposit{salt: deployFetchParams.swapID}(IERC20Lite(deployFetchParams.token));
    }

    /**
     * @notice  Retrieves any token from an address where a Deposit contract is already deployed.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param fetchParams    The fetch parameters
     */
    function fetch(SigData calldata sigData, FetchParams calldata fetchParams)
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    fetchParams
                )
            )
        )
    {
        _fetch(fetchParams);
    }

    /**
     * @notice  Retrieves any token from an address where a Deposit contract is already deployed.
     * @param fetchParams    The fetch parameters
     */
    function _fetch(FetchParams calldata fetchParams) private {
        try Deposit(fetchParams.fetchContract).fetch(IERC20Lite(fetchParams.token)) {} catch {
            emit FetchFailed(fetchParams.fetchContract, fetchParams.token);
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //         Initiate cross-chain swaps (source chain)        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Swaps native token for a token in another chain. The egress token will be transferred to the specified 
     *          destination address on the destination chain.
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
     * @notice  Swaps ERC20 token for a token in another chain. The desired token will be transferred to the specified 
     *          destination address on the destination chain. The provided ERC20 token must be supported by the Chainflip Protocol. 
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity indicate that an amount is required.

     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    String containing the destination address on the destination chain.
     * @param swapIntent    String containing the specifics of the swap to be performed according to Chainflip's nomenclature.
     * @param srcToken      Address of the source token to swap.
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
    //     Initiate cross-chain call and swap (source chain)    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Performs a cross-chain call to the destination address on the destination chain. Native tokens must be paid
     *          to this contract. The swap intent determines if the provided tokens should be swapped to a different token
     *          and transferred as part of the cross-chain call. Otherwise, all tokens are used as a payment for gas on the destination chain.
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
     * @param dstNativeGas  The amount of native gas to be used on the destination chain's call.
     * @param refundAddress Address to refund any excess gas left from the execution of the xCall on the dstChain. This address
     *                      is in the context of the srcChain.
     */
    function xCallNative(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        uint256 dstNativeGas,
        address refundAddress
    ) external payable override onlyNotSuspended xCallsEnabled nzUint(msg.value) {
        emit XCallNative(dstChain, dstAddress, swapIntent, msg.value, msg.sender, message, dstNativeGas, refundAddress);
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
     * @param dstNativeGas  The amount of native gas to be used on the destination chain's call. That gas will be paid with the
     *                      source token.
     * @param srcToken      Address of the source token.
     * @param amount        Amount of tokens to swap.
     * @param refundAddress Address to refund any excess gas left from the execution of the xCall on the dstChain. This address
     *                      is in the context of the srcChain.
     */
    function xCallToken(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        uint256 dstNativeGas,
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
            dstNativeGas,
            refundAddress
        );
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //      Execute cross-chain call and swap (dest. chain)     //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Transfers ETH or a token from this vault to a recipient and makes a function call
     *          completing a cross-chain swap and call. The ICFReceiver interface is expected on
     *          the receiver's address. A message is passed to the receiver along with other
     *          parameters specifying the origin of the swap.
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally a hash over
     *                  the calldata to the function with an empty sigData) and sig over that
     *                  that hash (uint) from the aggregate key.
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
        // Logic in another internal function to avoid the stackTooDeep error
        _executexSwapAndCall(transferParams, srcChain, srcAddress, message);
    }

    /**
     * @notice Logic for transferring the tokens and calling the recipient. It's on the receiver to
     *         make sure the call doesn't revert, otherwise the tokens won't be transferred.
     *         The _transfer function is not used because we want to be able to embed the native token
     *         into the cfReceive call to avoid doing two external calls.
     *         In case of revertion the tokens will remain in the Vault. Therefore, the destination
     *         contract must ensure it doesn't revert e.g. using try-catch mechanisms.
     */
    function _executexSwapAndCall(
        TransferParams calldata transferParams,
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) private {
        if (transferParams.token == _NATIVE_ADDR) {
            ICFReceiver(transferParams.recipient).cfReceive{value: transferParams.amount}(
                srcChain,
                srcAddress,
                message,
                transferParams.token,
                transferParams.amount
            );
        } else {
            IERC20(transferParams.token).safeTransfer(transferParams.recipient, transferParams.amount);
            ICFReceiver(transferParams.recipient).cfReceive(
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
    //          Execute cross-chain call (dest. chain)          //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Executes a cross-chain function call. The ICFReceiver interface is expected on
     *          the receiver's address. A message is passed to the receiver along with other
     *          parameters specifying the origin of the swap. This is used for cross-chain messaging
     *          without any swap taking place on the Chainflip Protocol.
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
        ICFReceiver(recipient).cfReceivexCall(srcChain, srcAddress, message);
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

        // Transfer all native and ERC20 Tokens
        for (uint256 i = 0; i < tokens.length; i++) {
            if (tokens[i] == _NATIVE_ADDR) {
                _transfer(_NATIVE_ADDR, recipient, address(this).balance);
            } else {
                _transfer(tokens[i], recipient, IERC20(tokens[i]).balanceOf(address(this)));
            }
        }
    }

    /**
     * @notice  Enable swapNative and swapToken functionality by governance. Features disabled by default
     */
    function enablexCalls() external override onlyGovernor xCallsDisabled {
        _xCallsEnabled = true;
        emit XCallsEnabled(true);
    }

    /**
     * @notice  Disable swapNative and swapToken functionality by governance. Features disabled by default.
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

    /// @dev    Check that no nonce has been consumed in the last 14 days - emergency
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

    /// @dev For receiving native when Deposit.fetch() is called.
    receive() external payable {}
}
