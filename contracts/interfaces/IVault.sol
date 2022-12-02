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

    function fetchDepositEth(SigData calldata sigData, bytes32 swapID) external;

    function fetchDepositEthBatch(SigData calldata sigData, bytes32[] calldata swapIDs) external;

    function fetchDepositToken(SigData calldata sigData, FetchParams calldata fetchParams) external;

    function fetchDepositTokenBatch(SigData calldata sigData, FetchParams[] calldata fetchParamsArray) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                 SrcChain xSwap and call                  //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xCallToken(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        IERC20 srcToken,
        uint256 amount,
        address refundAddress
    ) external;

    function xCallNative(
        uint32 dstChain,
        string memory dstAddress,
        string memory swapIntent,
        bytes calldata message,
        address refundAddress
    ) external payable;

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
