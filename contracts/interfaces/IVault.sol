pragma solidity ^0.8.0;


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

    function transferBatch(
        SigData calldata sigData,
        address[] calldata tokenAddrs,
        address payable[] calldata recipients,
        uint[] calldata amounts
    ) external;

    function fetchDepositEth(
        SigData calldata sigData,
        bytes32 swapID
    ) external;

    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        address tokenAddr
    ) external;

    function fetchDepositBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        address[] calldata tokenAddrs
    ) external;


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////


    function getKeyManager() external returns (IKeyManager);
}
