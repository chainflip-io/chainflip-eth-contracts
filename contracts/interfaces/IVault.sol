pragma solidity ^0.8.0;

import "./IAggKeyNonceConsumer.sol";
import "./IGovernanceCommunityGuarded.sol";

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

    function deployAndFetch(SigData calldata sigData, DeployFetchParams calldata deployFetchParams) external;

    function fetch(SigData calldata sigData, FetchParams calldata fetchParams) external;

    function fetchBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParams,
        FetchParams[] calldata fetchParams
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                 SrcChain xSwap and call                  //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xCallNative(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        uint256 dstNativeGas,
        address refundAddress
    ) external payable;

    function xCallToken(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        uint256 dstNativeGas,
        IERC20 srcToken,
        uint256 amount,
        address refundAddress
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                    SrcChain xSwap                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xSwapToken(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        IERC20 srcToken,
        uint256 amount
    ) external;

    function xSwapNative(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent
    ) external payable;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //             DstChain receive xSwap and call              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function executexSwapAndCall(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                   DstChain receive xcall                 //
    //                                                          //
    //////////////////////////////////////////////////////////////
    function executexCall(
        SigData calldata sigData,
        address recipient,
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Governance                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function govWithdraw(address[] calldata tokens) external;

    function enablexCalls() external;

    function disablexCalls() external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getxCallsEnabled() external view returns (bool);
}
