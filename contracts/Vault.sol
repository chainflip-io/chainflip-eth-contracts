pragma solidity ^0.8.0;


import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
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

    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;


    constructor(IKeyManager keyManager) {
        _keyManager = keyManager;
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
     * @notice  Retrieves ETH from an address deterministically generated using
     *          create2 by creating a contract for that address, sending it to this vault, and
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
     * @notice  Retrieves ETH or a token from an address deterministically generated using
     *          create2 by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and 
     *                  sig over that hash (uint) from the aggregate key
     * @param swapID    The unique identifier for this swap (bytes32)
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

    // function batch

    function fetchDepositBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        address[] calldata tokenAddrs
    ) external override validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.fetchDepositBatch.selector,
                SigData(0, 0),
                swapIDs,
                tokenAddrs
            )
        ),
        KeyID.Agg
    ) {
        require(swapIDs.length == tokenAddrs.length, "Vault: arrays not same length");

        for (uint i; i < swapIDs.length; i++) {
            if (tokenAddrs[i] == _ETH_ADDR) {
                new DepositEth{salt: swapIDs[i]}();
            } else {
                new DepositToken{salt: swapIDs[i]}(IERC20Lite(tokenAddrs[i]));
            }
        }
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
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

    
    /// @dev    Call isValidSig in _keyManager
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