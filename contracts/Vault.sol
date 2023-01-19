pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./interfaces/IVault.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IERC20Lite.sol";
import "./abstract/Shared.sol";
import "./Deposit.sol";
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
     *          deposits , then it performs all transfers specified with the rest
     *          of the inputs, the same as transferBatch (where all inputs are again required
     *          to be of equal length - however the lengths of the fetch inputs do not have to
     *          be equal to lengths of the transfer inputs). Fetches/transfers of ETH are indicated
     *          with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address. It is assumed
     *          that the elements of each array match in terms of ordering, i.e. a given
     *          fetch should should have the same index swapIDs[i] and tokens[i]
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
     *          address using create2, by creating a contract for that address and sending it to this vault,
     *          or by calling the fetch function of an already deployed Deposit contract.
     * @dev     FetchAndDeploy is executed first to handle the edge case , which probably shouldn't
     *          happpen anyway, where a deploy and a fetch for the same address in the same batch.
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
            new Deposit{salt: deployFetchParamsArray[i].swapID}(IERC20Lite(address(deployFetchParamsArray[i].token)));
            unchecked {
                ++i;
            }
        }

        // Fetch from already deployed contracts
        length = fetchParamsArray.length;
        for (i = 0; i < length; ) {
            Deposit(fetchParamsArray[i].fetchContract).fetch(IERC20Lite(fetchParamsArray[i].token));
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
        new Deposit{salt: deployFetchParams.swapID}(IERC20Lite(address(deployFetchParams.token)));
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
        Deposit(fetchParams.fetchContract).fetch(IERC20Lite(fetchParams.token));
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
        onlyNotSuspended
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
        onlyNotSuspended
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
                _transfer(IERC20(_ETH_ADDR), recipient, address(this).balance);
            } else {
                _transfer(tokens[i], recipient, tokens[i].balanceOf(address(this)));
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
