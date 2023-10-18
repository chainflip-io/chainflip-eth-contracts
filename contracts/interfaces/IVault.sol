// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./IAggKeyNonceConsumer.sol";
import "./IGovernanceCommunityGuarded.sol";
import "./IMulticall.sol";

/**
 * @title    Vault interface
 * @notice   The interface for functions Vault implements
 */
interface IVault is IGovernanceCommunityGuarded, IAggKeyNonceConsumer {
    event FetchedNative(address indexed sender, uint256 amount);

    event TransferNativeFailed(address payable indexed recipient, uint256 amount);
    event TransferTokenFailed(address payable indexed recipient, uint256 amount, address indexed token, bytes reason);

    event SwapNative(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        uint256 amount,
        address indexed sender,
        bytes cfParameters
    );
    event SwapToken(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        address srcToken,
        uint256 amount,
        address indexed sender,
        bytes cfParameters
    );

    /// @dev bytes parameters is not indexed because indexing a dynamic type for it to be filtered
    ///      makes it so we won't be able to decode it unless we specifically search for it. If we want
    ///      to filter it and decode it then we would need to have both the indexed and the non-indexed
    ///      version in the event. That is unnecessary.
    event XCallNative(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        uint256 amount,
        address indexed sender,
        bytes message,
        uint256 gasAmount,
        bytes cfParameters
    );
    event XCallToken(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        address srcToken,
        uint256 amount,
        address indexed sender,
        bytes message,
        uint256 gasAmount,
        bytes cfParameters
    );

    event AddGasNative(bytes32 swapID, uint256 amount);
    event AddGasToken(bytes32 swapID, uint256 amount, address token);

    event ExecuteActionsFailed(
        address payable indexed multicallAddress,
        uint256 amount,
        address indexed token,
        bytes reason
    );

    function allBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    ) external;

    function allBatchV2(
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

    function transferFallback(SigData calldata sigData, TransferParams calldata transferParams) external;

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
