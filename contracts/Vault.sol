pragma solidity ^0.8.0;


import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./interfaces/IVault.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IERC20Lite.sol";
import "./abstract/Shared.sol";
import "./DepositEth.sol";
import "./DepositToken.sol";


/**
* @title    Vault contract
* @notice   The vault for holding ETH/tokens and deploying contracts
*           for fetching individual deposits
* @author   Quantaf1re (James Key)
*/
contract Vault is IVault, Shared {

    using SafeERC20 for IERC20;

    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private immutable _keyManager;


    event TransferFailed(
        address payable indexed recipient,
        uint amount,
        bytes lowLevelData
    );


    constructor(IKeyManager keyManager) {
        _keyManager = keyManager;
    }


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
        uint[] calldata tranAmounts
    ) external override refundGas updatedValidSig(
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
        ),
        KeyID.AGG
    ) {
        // Can't put these as modifiers annoyingly because it creates
        // a 'stack too deep' error
        require(
            fetchSwapIDs.length == fetchTokens.length &&
            tranTokens.length == tranRecipients.length &&
            tranRecipients.length == tranAmounts.length,
            "Vault: arrays not same length"
        );

        // Fetch all deposits
        for (uint i = 0; i < fetchSwapIDs.length; i++) {
            if (address(fetchTokens[i]) == _ETH_ADDR) {
                new DepositEth{salt: fetchSwapIDs[i]}();
            } else {
                new DepositToken{salt: fetchSwapIDs[i]}(IERC20Lite(address(fetchTokens[i])));
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
        uint amount
    ) external override nzAddr(address(token)) nzAddr(recipient) nzUint(amount) updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.transfer.selector,
                SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                token,
                recipient,
                amount
            )
        ),
        KeyID.AGG
    ) {
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
        uint[] calldata amounts
    ) external override refundGas updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.transferBatch.selector,
                SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                tokens,
                recipients,
                amounts
            )
        ),
        KeyID.AGG
    ) {
        require(
            tokens.length == recipients.length &&
            recipients.length == amounts.length,
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
        uint[] calldata amounts
    ) private {
        for (uint i = 0; i < tokens.length; i++) {
            _transfer(tokens[i], recipients[i], amounts[i]);
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
        uint amount
    ) private {
        if (address(token) == _ETH_ADDR) {
            try this.sendEth{value: amount}(recipient) {
            } catch (bytes memory lowLevelData) {
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
     * @notice  Retrieves ETH from an address, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param swapID    The unique identifier for this swap (bytes32)
     */
    function fetchDepositEth(
        SigData calldata sigData,
        bytes32 swapID
    ) external override nzBytes32(swapID) refundGas updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositEth.selector,
                SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                swapID
            )
        ),
        KeyID.AGG
    ) {
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
    function fetchDepositEthBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs
    ) external override refundGas updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositEthBatch.selector,
                SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                swapIDs
            )
        ),
        KeyID.AGG
    ) {
        for (uint i; i < swapIDs.length; i++) {
            new DepositEth{salt: swapIDs[i]}();
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
    ) external override nzBytes32(swapID) nzAddr(address(token)) refundGas updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositToken.selector,
                SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                swapID,
                token
            )
        ),
        KeyID.AGG
    ) {
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
    ) external override refundGas updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositTokenBatch.selector,
                SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                swapIDs,
                tokens
            )
        ),
        KeyID.AGG
    ) {
        require(
            swapIDs.length == tokens.length,
            "Vault: arrays not same length"
        );

        for (uint i; i < swapIDs.length; i++) {
            new DepositToken{salt: swapIDs[i]}(IERC20Lite(address(tokens[i])));
        }
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external view override returns (IKeyManager) {
        return _keyManager;
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////


    /// @dev    Calls isUpdatedValidSig in _keyManager
    modifier updatedValidSig(
        SigData calldata sigData,
        bytes32 contractMsgHash,
        KeyID keyID
    ) {
        require(_keyManager.isUpdatedValidSig(sigData, contractMsgHash, keyID));
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