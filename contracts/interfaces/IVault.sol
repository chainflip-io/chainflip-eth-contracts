pragma solidity ^0.8.7;


import "./IShared.sol";
import "./IKeyManager.sol";


/**
* @title    Vault interface
* @notice   The interface for functions Vault implements
* @author   Quantaf1re (James Key)
*/
interface IVault is IShared {

    function allBatch(
        SigData calldata sigData,
        bytes32[] calldata fetchSwapIDs,
        address[] calldata fetchTokenAddrs,
        address[] calldata tranTokenAddrs,
        address payable[] calldata tranRecipients,
        uint[] calldata tranAmounts
    ) external;


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Transfers                       //
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


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Fetch Deposits                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function fetchDepositEth(
        SigData calldata sigData,
        bytes32 swapID
    ) external;

    function fetchDepositEthBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs
    ) external;

    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        address tokenAddr
    ) external;

    function fetchDepositTokenBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        address[] calldata tokenAddrs
    ) external;


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getKeyManager() external returns (IKeyManager);
}
