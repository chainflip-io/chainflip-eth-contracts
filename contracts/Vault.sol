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

    // We don't index the egressAddress because it's a string (dynamicType). If we index it to be able to filter,
    // then unless we specically search for it we won't be able to decode it.
    // See: https://ethereum.stackexchange.com/questions/6840/indexed-event-with-string-not-getting-logged
    event SwapETH(string egressParams, string egressAddress, bytes message, uint256 amount, address indexed sender);
    event SwapToken(
        string egressParams,
        string egressAddress,
        bytes message,
        address ingressToken,
        uint256 amount,
        address indexed sender
    );
    event CCM(string egressChain, string egressAddress, bytes message, address indexed sender);

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
    //                        Swaps                             //
    //                                                          //
    //////////////////////////////////////////////////////////////

    // Input params:
    // 1. bytes memory/calldata message
    // 2. egress chain (string vs uint16 vs uint32). COuld be the chainID or just a number that in CF we map to a chain.
    //      LZ uses their own chainId numerology
    //      Connext also does that
    //      Axelar has their specific strings
    // 3. egress address (bytes32 or bytes or string to be more flexible? address is limiting to EVM).
    //      BTC addresses are 26-35 characters long => Google says approximately 25 bytes but I don't know..
    //      Also, converting that address into bytes might be extremely confusing. So I would fo for a string
    //      for the egress address. The only downside is that it's not as gas efficient as bytes.
    //      Example BTC address: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
    //                => converted to bytes in Solidity:   0x20626331717879326b676479676a727371747a71326e30797266323439337038336b6b666a687830776c68
    //                => that is more than 32 bytes:       0x626c756500000000000000000000000000000000000000000000000000000000
    //                =>  representation before address is (https://en.bitcoin.it/wiki/Technical_background_of_version_1_Bitcoin_addresses)
    //                    converted into base  58 encoded: 0x00f54a5851e9372b87810a8e60cdd2e7cfd80b6e31
    //      So it seems like there is a way to get BTC addresses in 25 bytes
    //      So we could potentially only use bytes (not bytes32). Both could work. For BTC, having the address in bytes is very confusing,
    //      although for other chains. Also, looks like Solana addresses are similar to BTC (2zL8VtonfKdGxj15qwF1vi8xHPcrC89WWNDccq2tFMP9)
    //      potentially even longer (32-55 characters). So it is not only BTC that will look weird on-chain if using bytes.
    //      SUI and APTOS are more friendly (32 hex characters).
    //
    // 4. egress token
    //      - address => This will limit the non-EVM chains.
    //      - string?
    //      - This could also be embedded in a egress address string (ETH:ETH) and the CF engine will translate
    //        it into the correct address. That is probably the most gas-efficient way to do it.
    //      - This could even be a bool (_isNative). This works if we only support two assets per chain. In ETH
    //        for example we support 3 (USDC/ETH/FLIP) so I don't think that would work. It also limits us
    //        in the future. Like before, the CF engine would need to convert it into the correct address.
    //      - uint => we could have a mapping of uint => token for each chain. Would be a lot more gas efficient and
    //        easier to integrate with other protocols.
    // 5- ingress token => This needs to be an address/ERC20 (isNative would be a mess and potentially not work with 3 assets)
    // 6. amount: Only needed for non-native tokens. For native tokens, we can use msg.value.

    // Should we split this into two functions, one for native and one for non-native?
    // Should we have the non-cross message in a separate function? Or just mark it with empty message?

    // TLDR: BTC and Solana (and maybe others) have addresses expressed in characters (non-hex). They can maybe be expressed in
    // less than 32 bytes but there would need to be some non-intuitive conversion. A conversion from the address in string to
    // bytes would be also confusing to read on-chain and the final result is >32 bytes.
    // For addresses in 32 bytes it is more expensive to use string and also to use bytes. For more than 32 bytes, we can use bytes
    // or string. The gas usage of both is exactly the same (assuming we are converting stringToBytes as Solidity would do).
    // Therefore, I would go for a string which is more readable on-chain and very flexible - allow for all chains.

    // So the remaining questions are:
    // 1. Can/should we just represent the egress address as a uint or string? String will definitely take more gas but we can pack it with other egress,
    // althought that will still me more gas costly. Depends on future flexibility (although uint should be enough) and mainly on clarity and ease for CFE.
    // 2. EgressToken and EgressAddress seem to need a string. Then the CFE will translate it to addresses in the egress chain. Should we pack them?
    // 3. If we pack the two previous values, should we also pack it with the first one? Or have two separate strings, one with the egress chain
    // and egress token, and the other one with the egress address. The only upside there would be clarity.
    // If we pack them all together we could separate them with ":" or something, so we can split them in the CFE.
    // Packing all them would especially be good since the string overhead will be only once. However, egress chain would still be cheaper with a uint,
    // and I am not sure how we feel about the clarity of "BTC:BTC:bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", espeically for hex addresses with
    // the "0x" at the beginning "ETH:USDC:0x362fA9D0bCa5D19f743Db50738345ce2b40eC99f".


    // EgressParams being egressChain:egressToken
    // We could have egressParams be two uints (same gas) and map each uint to a chain and a token.
    // In the function call the parameters are not packed, so it doesnt matter if it's two uint256 or two uint32.
    // Actually, string concatenation after solidity 8.12 is easy, just string.concat(). But the code will need to concat with ":". It costs
    // gas but it's OK to ask that since it will normally come externally. If it doesn't they can just concatenate it.
    // Checking non-empty string (egressParams/egressAddress) is a bit of a waste of gas, so we don't do it.
    // Also, because a non-empty string doesn't mean it's a valid egressAddress anyway. That checking should
    // be done by the CFE.
    // TODO: if we refund we need to add a refund address. For example, if LiFi is in the middle, we want to refund the user, not LiFi.
    // This is the case if we do a retrospective refund.
    // TODO: Think about error handling (e.g. addGas? How do we then refer to a specific transaction? transferID? Counter? Nonce?
    //       Or we just give the transaction to the user to send?
    // TODO: If we want to allow gas topups then a txHash parameter should be use as an input to match with the transaction. This way
    //       there wouldn't be a need to add a transferID at the smart contract level. But then the SC needs to keep track of that.
    // TODO: Do we want a pure CCM call without token swapping?. I think so.
    // TODO: Do we prefer uint for egressChain and egress token or a single string? Gaswise the uints are just a bit cheaper (not too relevant)
    //       However, that would be great for the egress part, since we only pass egress chain there.

    /**
     * @notice  Swaps ERC20 Token for a token in another chain. Function call needs to specify the ingress and egress parameters.
     *          It also has a cross-chain message capability. An empty message signifies that only a token swap is to be performed.
     * @param egressParams  String containing egressChain and egressToken. Most likely egressChain:egressToken. In
     *                      the event of this not coming from calldata, it can easily be concatenated after 
     *                      after solidity 8.12 with string.concat().
     *                      We could also make this two parameters two uints which is slightly cheaper gas-wise.
     * @param egressAddress String containing the egress address. In case of the sending contract having to craft
     *                      the egress address from an EVM address type, string(abi.encodePacked(input)) can be used.
     *                      So I don't think we need a specific EVM function for that with an address parameter.
     * @param message       String containing the message to be sent to the egress chain. Can be empty.
     * @param ingressToken  Address of the token to swap.
     * @param amount        Amount of tokens to swap.
     */
    function swapToken(
        string memory egressParams,
        string memory egressAddress,
        bytes calldata message,
        IERC20 ingressToken,
        uint256 amount
    ) external payable onlyNotSuspended swapsEnabled nzUint(amount) {
        ingressToken.safeTransferFrom(msg.sender, address(this), amount);
        emit SwapToken(egressParams, egressAddress, message, address(ingressToken), amount, msg.sender);
    }

    function swapETH(
        string memory egressParams,
        string memory egressAddress,
        bytes calldata message
    ) external payable onlyNotSuspended swapsEnabled nzUint(msg.value) {
        // The check for existing parameters shall be done in the CFE
        emit SwapETH(egressParams, egressAddress, message, msg.value, msg.sender);
    }

    function ccm(
        string memory egressChain,
        string memory egressAddress,
        bytes calldata message
    ) external payable onlyNotSuspended swapsEnabled {
        // The check for existing parameters shall be done in the CFE
        emit CCM(egressChain, egressAddress, message, msg.sender);
    }

    // Source token is not really needed right? if so, I'm not sure it should be part of that string, since it's probably not what the user would want to check.
    // Separating ingressChain and ingressAddress because if they want to be checked separately it's extremely painful to split them in solidity.
    function crossChainMessage(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        string calldata ingressChain,
        string calldata ingressAddress,
        bytes calldata message
    )
        external
        onlyNotSuspended
        nzAddr(address(transferParams.token))
        nzAddr(transferParams.recipient)
        nzUint(transferParams.amount)
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.crossChainMessage.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    transferParams,
                    ingressChain,
                    ingressAddress,
                    message
                )
            )
        )
    {
        // Copying the used parameters to mempory to avoid StackTooDeep error. To play a bit more with it
        // since we are probably spending more gas here.
        uint256 amount = transferParams.amount;
        address token = address(transferParams.token);
        address payable recipient = transferParams.recipient;
         _transfer(token, recipient, amount);
        ICFReceiver(recipient).cfRecieve(ingressChain, ingressAddress, message, token, amount);
    }

    //TODO: Decide if we need this or we just take it as subset of transferWithMessage (with amount = 0).
    // This would be to have a specialized CCM messaging functionality. I think it would be good to have
    // so we don't have to pass a token an amount which doesn't make sense and wastes gas.
    // Even if we don't implement that straight away in Rust, it's good to have already in the SC.

    // Ingress params = SourceChain:sourceAddress
    // Do we want to have this? Or do we need this? It would be for cross-chain messaging without token transfer.
    // I think that if we are not reaching the MAX bytecodesize we should have this for future-proofing.
    function messageWithoutTransfer(
        SigData calldata sigData,
        address recipient,
        string calldata ingressChain,
        string calldata ingressAddress,
        bytes calldata message
    )
        external
        onlyNotSuspended
        nzAddr(recipient)
        consumesKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.messageWithoutTransfer.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    recipient,
                    ingressChain,
                    ingressAddress,
                    message
                )
            )
        )
    {
        ICFReceiver(recipient).cfRecieveMessage(ingressChain, ingressAddress, message);
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
