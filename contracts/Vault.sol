pragma solidity ^0.8.0;


import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/IVault.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/ITreasury.sol";
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

    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;
    /// @dev    The Treasury which lends out most of the assets held
    ///         by CF on Ethereum
    ITreasury private _treasury;
    // Lending parameters
    /// @dev    The upper bound percent of an asset held by CF contracts on ETH such
    ///         that enough is lent out to return it to the mid range of the bounds.
    ///         Max BPS is 10000
    uint constant public UPPER_LEND_BPS = 2000;
    /// @dev    The lower bound percent of an asset held by CF contracts on ETH such
    ///         that enough is withdrawn from lending platforms to return it
    ///         to the mid range of the bounds. Max BPS is 10000
    uint constant public LOWER_LEND_BPS = 1000;


    constructor(IKeyManager keyManager, ITreasury treasury) {
        _keyManager = keyManager;
        // Might want to change this to creating the contract
        // here instead? Can't do it yet without an implementation
        // of treasury
        _treasury = treasury;
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
     * @param tokenAddr The address of the token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei (uint)
     */
    function transfer(
        SigData calldata sigData,
        address tokenAddr,
        address payable recipient,
        uint amount
    ) external override nzAddr(tokenAddr) nzAddr(recipient) nzUint(amount) validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.transfer.selector,
                SigData(0, 0),
                tokenAddr,
                recipient,
                amount
            )
        ),
        KeyID.Agg
    ) {
        _transfer(tokenAddr, recipient, amount);
    }

    /**
     * @notice  Transfers ETH or tokens from this vault to a recipients. It is assumed
     *          that the elements of each array match in terms of ordering, i.e. a given
     *          transfer should should have the same index tokenAddrs[i], recipients[i],
     *          and amounts[i].
     * @param sigData   The keccak256 hash over the msg (uint) (here that's
     *                  a hash over the calldata to the function with an empty sigData) and 
     *                  sig over that hash (uint) from the aggregate key
     * @param tokenAddrs The addresses of the tokens to be transferred
     * @param recipients The address of the recipient of the transfer
     * @param amounts    The amount to transfer, in wei (uint)
     */
    function transferBatch(
        SigData calldata sigData,
        address[] calldata tokenAddrs,
        address payable[] calldata recipients,
        uint[] calldata amounts
    ) external override validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.transferBatch.selector,
                SigData(0, 0),
                tokenAddrs,
                recipients,
                amounts
            )
        ),
        KeyID.Agg
    ) {
        require(
            tokenAddrs.length == recipients.length &&
            recipients.length == amounts.length, 
            "Vault: arrays not same length"
        );

        for (uint i; i < tokenAddrs.length; i++) {
            _transfer(tokenAddrs[i], recipients[i], amounts[i]);
        }
    }

    /**
     * @notice  Transfers ETH or a token from this vault to a recipient
     * @param tokenAddr The address of the token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei (uint)
     */
    function _transfer(
        address tokenAddr,
        address payable recipient,
        uint amount
    ) private {
        if (tokenAddr == _ETH_ADDR) {
            recipient.transfer(amount);
        } else {
            // It would be nice to wrap require around this line, but
            // some older tokens don't return a bool
            IERC20(tokenAddr).transfer(recipient, amount);
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
    ) external override nzBytes32(swapID) validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositEth.selector,
                SigData(0, 0),
                swapID
            )
        ),
        KeyID.Agg
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
    ) external override validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositEthBatch.selector,
                SigData(0, 0),
                swapIDs
            )
        ),
        KeyID.Agg
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
     * @param tokenAddr The address of the token to be transferred
     */
    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        address tokenAddr
    ) external override nzBytes32(swapID) nzAddr(tokenAddr) validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositToken.selector,
                SigData(0, 0),
                swapID,
                tokenAddr
            )
        ),
        KeyID.Agg
    ) {
        new DepositToken{salt: swapID}(IERC20Lite(tokenAddr));
    }

    /**
     * @notice  Retrieves tokens from multiple addresses, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and 
     *                  sig over that hash (uint) from the aggregate key
     * @param swapIDs       The unique identifiers for this swap (bytes32), used for create2
     * @param tokenAddrs    The addresses of the tokens to be transferred
     */
    function fetchDepositTokenBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        address[] calldata tokenAddrs
    ) external override validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositTokenBatch.selector,
                SigData(0, 0),
                swapIDs,
                tokenAddrs
            )
        ),
        KeyID.Agg
    ) {
        require(
            swapIDs.length == tokenAddrs.length,
            "Vault: arrays not same length"
        );

        for (uint i; i < swapIDs.length; i++) {
            new DepositToken{salt: swapIDs[i]}(IERC20Lite(tokenAddrs[i]));
        }
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Treasury                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Checks whether a group of tokens are above or below the upper bounds
     *          of this Vault 'hot wallet', and rebalances the wallet if outside those
     *          bounds by lending some out or withdrawing some back in.
     * @param tokens    The array (address[]) of tokens to check the balances/bounds of
     */
    function balanceTreasury(IERC20[] calldata tokens) external {
        for (uint i; i < tokens.length; i++) {
            uint vaultBal;
            uint treasuryBal = _treasury.getLentAmount(tokens[i]);

            if (address(tokens[i]) == _ETH_ADDR) {
                vaultBal = address(this).balance;
            } else {
                vaultBal = tokens[i].balanceOf(address(this));
            }

            uint totalBal = vaultBal + treasuryBal;
            uint percent = _MAX_BPS * vaultBal / totalBal;
            uint targetPercent = (UPPER_LEND_BPS + LOWER_LEND_BPS) / 2;

            if (percent > UPPER_LEND_BPS) {
                uint amount = (percent - targetPercent) * totalBal;

                if (address(tokens[i]) == _ETH_ADDR) {
                    payable(address(_treasury)).transfer(amount);
                } else {
                    tokens[i].transfer(address(_treasury), amount);
                }

                _treasury.lend();
            } else if (percent < LOWER_LEND_BPS) {
                uint amount = (targetPercent - percent) * totalBal;
                _treasury.withdraw(tokens[i], amount);
            }
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

    
    /// @dev    Calls isValidSig in _keyManager
    modifier validSig(
        SigData calldata sigData,
        bytes32 contractMsgHash,
        KeyID keyID
    ) {
        require(_keyManager.isValidSig(sigData, contractMsgHash, keyID));
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