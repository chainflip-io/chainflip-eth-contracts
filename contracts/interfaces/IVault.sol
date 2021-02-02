pragma solidity ^0.7.0;
pragma abicoder v2;


import "./IShared.sol";
import "./IKeyManager.sol";


/**
* @title    Vault interface
* @notice   The interface for functions Vault implements
* @author   Quantaf1re (James Key)
*/
interface IVault is IShared {

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function transfer(
        SigData calldata sigData,
        address tokenAddr,
        address payable recipient,
        uint amount
    ) external;

    function fetchDeposit(
        SigData calldata sigData,
        bytes32 swapID,
        address tokenAddr,
        uint amount
    ) external;


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////


    function getKeyManager() external returns (IKeyManager);
}
