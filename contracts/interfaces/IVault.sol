pragma solidity ^0.8.0;

import "./IAggKeyNonceConsumer.sol";
import "./IGovernanceCommunityGuarded.sol";
import "./IMulticall.sol";

/**
 * @title    Vault interface
 * @notice   The interface for functions Vault implements
 */
interface IVault is IGovernanceCommunityGuarded, IAggKeyNonceConsumer {
    function allBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Transfers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function transfer(SigData calldata sigData, TransferParams calldata transferParams) external;

    function transferBatch(SigData calldata sigData, TransferParams[] calldata transferParamsArray) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Fetch Deposits                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function deployAndFetchBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray
    ) external;

    function fetchBatch(SigData calldata sigData, FetchParams[] calldata fetchParamsArray) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //         Initiate cross-chain swaps (source chain)        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xSwapToken(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external;

    function xSwapNative(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata cfParameters
    ) external payable;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //     Initiate cross-chain call and swap (source chain)    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xCallNative(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 gasAmount,
        bytes calldata cfParameters
    ) external payable;

    function xCallToken(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 gasAmount,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                     Gas topups                           //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function addGasNative(bytes32 swapID) external payable;

    function addGasToken(bytes32 swapID, uint256 amount, IERC20 token) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //      Execute cross-chain call and swap (dest. chain)     //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function executexSwapAndCall(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //          Execute cross-chain call (dest. chain)          //
    //                                                          //
    //////////////////////////////////////////////////////////////
    function executexCall(
        SigData calldata sigData,
        address recipient,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                 Auxiliary chain actions                  //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function executeActions(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        IMulticall.Call[] calldata calls,
        uint256 gasMulticall
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Governance                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function govWithdraw(address[] calldata tokens) external;
}
