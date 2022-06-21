pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./interfaces/IVault.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IERC20Lite.sol";
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
    event SwapETH(uint256 amount, string egressParams, bytes32 egressReceiver);
    event SwapToken(address ingressToken, uint256 amount, string egressParams, bytes32 egressReceiver);

    bool private _swapsEnabled;

    constructor(IKeyManager keyManager) AggKeyNonceConsumer(keyManager) {}

    /// @dev   Get the governor address from the KeyManager. This is called by the isGovernor
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
     * @param fetchSwapIDs      The unique identifiers for this swap (bytes32[]), used for create2
     * @param fetchTokens   The addresses of the tokens to be transferred
     * @param tranTokens    The addresses of the tokens to be transferred
     * @param tranRecipients    The address of the recipient of the transfer
     * @param tranAmounts       The amount to transfer, in wei (uint)
     */
    function allBatch(
        SigData calldata sigData,
        bytes32[] calldata fetchSwapIDs,
        IERC20[] calldata fetchTokens,
        IERC20[] calldata tranTokens,
        address payable[] calldata tranRecipients,
        uint256[] calldata tranAmounts
    )
        external
        override
        isNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.allBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    fetchSwapIDs,
                    fetchTokens,
                    tranTokens,
                    tranRecipients,
                    tranAmounts
                )
            )
        )
    {
        // Can't put these as modifiers annoyingly because it creates
        // a 'stack too deep' error
        require(
            fetchSwapIDs.length == fetchTokens.length &&
                tranTokens.length == tranRecipients.length &&
                tranRecipients.length == tranAmounts.length,
            "Vault: arrays not same length"
        );

        // Fetch all deposits
        uint256 length = fetchSwapIDs.length;
        for (uint256 i = 0; i < length; ) {
            if (address(fetchTokens[i]) == _ETH_ADDR) {
                new DepositEth{salt: fetchSwapIDs[i]}();
            } else {
                new DepositToken{salt: fetchSwapIDs[i]}(IERC20Lite(address(fetchTokens[i])));
            }
            unchecked {
                ++i;
            }
        }

        // Send all transfers
        _transferBatch(tranTokens, tranRecipients, tranAmounts);
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
     * @param token     The token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei (uint)
     */
    function transfer(
        SigData calldata sigData,
        IERC20 token,
        address payable recipient,
        uint256 amount
    )
        external
        override
        isNotSuspended
        nzAddr(address(token))
        nzAddr(recipient)
        nzUint(amount)
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.transfer.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    token,
                    recipient,
                    amount
                )
            )
        )
    {
        _transfer(token, recipient, amount);
    }

    /**
     * @notice  Transfers ETH or tokens from this vault to recipients. It is assumed
     *          that the elements of each array match in terms of ordering, i.e. a given
     *          transfer should should have the same index tokens[i], recipients[i],
     *          and amounts[i].
     * @param sigData   The keccak256 hash over the msg (uint) (here that's
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param tokens    The addresses of the tokens to be transferred
     * @param recipients The address of the recipient of the transfer
     * @param amounts    The amount to transfer, in wei (uint)
     */
    function transferBatch(
        SigData calldata sigData,
        IERC20[] calldata tokens,
        address payable[] calldata recipients,
        uint256[] calldata amounts
    )
        external
        override
        isNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.transferBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    tokens,
                    recipients,
                    amounts
                )
            )
        )
    {
        require(
            tokens.length == recipients.length && recipients.length == amounts.length,
            "Vault: arrays not same length"
        );

        _transferBatch(tokens, recipients, amounts);
    }

    /**
     * @notice  Transfers ETH or tokens from this vault to recipients. It is assumed
     *          that the elements of each array match in terms of ordering, i.e. a given
     *          transfer should should have the same index tokens[i], recipients[i],
     *          and amounts[i].
     * @param tokens The addresses of the tokens to be transferred
     * @param recipients The address of the recipient of the transfer
     * @param amounts    The amount to transfer, in wei (uint)
     */
    function _transferBatch(
        IERC20[] calldata tokens,
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) private {
        uint256 length = tokens.length;
        for (uint256 i = 0; i < length; ) {
            _transfer(tokens[i], recipients[i], amounts[i]);
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
        IERC20 token,
        address payable recipient,
        uint256 amount
    ) private {
        if (address(token) == _ETH_ADDR) {
            try this.sendEth{value: amount}(recipient) {} catch (bytes memory lowLevelData) {
                emit TransferFailed(recipient, amount, lowLevelData);
            }
        } else {
            token.safeTransfer(recipient, amount);
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Fetch Deposits                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

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
        isNotSuspended
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
        isNotSuspended
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
     * @param swapID    The unique identifier for this swap (bytes32), used for create2
     * @param token     The token to be transferred
     */
    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        IERC20 token
    )
        external
        override
        isNotSuspended
        nzBytes32(swapID)
        nzAddr(address(token))
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetchDepositToken.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    swapID,
                    token
                )
            )
        )
    {
        new DepositToken{salt: swapID}(IERC20Lite(address(token)));
    }

    /**
     * @notice  Retrieves tokens from multiple addresses, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param swapIDs       The unique identifiers for this swap (bytes32[]), used for create2
     * @param tokens        The addresses of the tokens to be transferred
     */
    function fetchDepositTokenBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        IERC20[] calldata tokens
    )
        external
        override
        isNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.fetchDepositTokenBatch.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    swapIDs,
                    tokens
                )
            )
        )
    {
        require(swapIDs.length == tokens.length, "Vault: arrays not same length");

        uint256 length = swapIDs.length;
        for (uint256 i; i < length; ) {
            new DepositToken{salt: swapIDs[i]}(IERC20Lite(address(tokens[i])));
            unchecked {
                ++i;
            }
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Swaps                             //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Swaps ETH for a token in another chain. Function call needs to specify egress parameters
     * @param egressParams  String containing egress parameters
     * @param egressReceiver  Egress reciever's address
     */
    function swapETH(string calldata egressParams, bytes32 egressReceiver)
        external
        payable
        override
        isNotSuspended
        swapsEnabled
        nzUint(msg.value)
        nzBytes32(egressReceiver)
    {
        // The check for existing chainID, egressToken string and egressReceiver shall be done in the CFE
        emit SwapETH(msg.value, egressParams, egressReceiver);
    }

    /**
     * @notice  Swaps ERC20 Token for a token in another chain. Function call needs to specify the ingress and egress parameters
     * @param egressParams  String containing egress parameters
     * @param egressReceiver  Egress reciever's address
     * @param ingressToken  Ingress ERC20 token's address
     * @param amount  Amount of ingress token to swap
     */
    function swapToken(
        string calldata egressParams,
        bytes32 egressReceiver,
        IERC20 ingressToken,
        uint256 amount
    )
        external
        override
        isNotSuspended
        swapsEnabled
        nzUint(amount)
        nzAddr(address(ingressToken))
        nzBytes32(egressReceiver)
    {
        ingressToken.safeTransferFrom(msg.sender, address(this), amount);
        // The check for existing egresschain, egressToken and egressReceiver shall be done in the CFE
        emit SwapToken(address(ingressToken), amount, egressParams, egressReceiver);
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
    function govWithdraw(IERC20[] calldata tokens)
        external
        override
        isGovernor
        isCommunityGuardDisabled
        isSuspended
        validTime
    {
        // Could use msg.sender or getGovernor() but hardcoding the get call just for extra safety
        address payable recipient = payable(getKeyManager().getGovernanceKey());

        // Transfer all ETH and ERC20 Tokens
        for (uint256 i = 0; i < tokens.length; i++) {
            if (address(tokens[i]) == _ETH_ADDR) {
                _transfer(IERC20(_ETH_ADDR), recipient, address(this).balance);
            } else {
                _transfer(tokens[i], recipient, tokens[i].balanceOf(address(this)));
            }
        }
    }

    /**
     * @notice  Enable swapETH and swapToken functionality by governance. Features disabled by default
     */
    function enableSwaps() external override isGovernor swapsDisabled {
        _swapsEnabled = true;
    }

    /**
     * @notice  Disable swapETH and swapToken functionality by governance. Features disabled by default.
     */
    function disableSwaps() external override isGovernor swapsEnabled {
        _swapsEnabled = false;
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
    modifier validTime() {
        require(
            block.timestamp - getKeyManager().getLastValidateTime() >= _AGG_KEY_EMERGENCY_TIMEOUT,
            "Vault: not enough delay"
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
