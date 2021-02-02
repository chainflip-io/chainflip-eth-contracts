pragma solidity ^0.7.0;
pragma abicoder v2;


import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/IVault.sol";
import "./interfaces/IKeyManager.sol";
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
    //                  State-changing functions                //
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
    ) external override nzAddr(tokenAddr) nzAddr(recipient) nzUint(amount) {
    // validate(
    //     keccak256(abi.encodeWithSelector(
    //         this.transfer.selector,
    //         _NULL,
    //         _NULL,
    //         tokenAddr,
    //         recipient,
    //         amount
    //     )),
    //     msgHash,
    //     sig,
    //     _aggregateKeyData.pubKeyX,
    //     _aggregateKeyData.pubKeyYParity,
    //     _aggregateKeyData.nonceTimesGAddr
    // )
        require(
            _keyManager.isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.transfer.selector,
                        SigData(0, 0),
                        tokenAddr,
                        recipient,
                        amount
                    )
                ),
                sigData,
                _keyManager.getAggregateKey()
            )
        );

        // When separating this into 2 fcns, remember to delete _ETH_ADDR in Shared
        if (tokenAddr == _ETH_ADDR) {
            recipient.transfer(amount);
        } else {
            // It would be nice to wrap require around this line, but
            // some older tokens don't return a bool
            IERC20(tokenAddr).transfer(recipient, amount);
        }
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
    function fetchDeposit(
        SigData calldata sigData,
        bytes32 swapID,
        address tokenAddr,
    ) external override nzBytes32(swapID) nzAddr(tokenAddr) {
        require(
            _keyManager.isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.fetchDeposit.selector,
                        SigData(0, 0),
                        swapID,
                        tokenAddr,
                        amount
                    )
                ),
                sigData,
                _keyManager.getAggregateKey()
            )
        );
        
        if (tokenAddr == _ETH_ADDR) {
            DepositEth d = new DepositEth{salt: swapID}();
        } else {
            DepositToken d = new DepositToken{salt: swapID}(tokenAddr);
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

    
    // TODO: add modifier for checking sig once we can use v0.8 and it
    // compiles. See comment with validate in KeyManager

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Fallbacks                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev For receiving ETH when fetchDeposit is called
    receive() external payable {}
}