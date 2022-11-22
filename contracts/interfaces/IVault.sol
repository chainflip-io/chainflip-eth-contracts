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
    //                Ingress swaps with CCM                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xswapTokenWithCall(
        string memory egressParams,
        string memory egressAddress,
        bytes calldata message,
        IERC20 ingressToken,
        uint256 amount,
        address refundAddress
    ) external;

    function xSwapNativeWithCall(
        string memory egressParams,
        string memory egressAddress,
        bytes calldata message,
        address refundAddress
    ) external payable;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                     Ingress Swaps                        //
    //                                                          //
    //////////////////////////////////////////////////////////////
    function xSwapToken(
        string memory egressParams,
        string memory egressAddress,
        IERC20 ingressToken,
        uint256 amount
    ) external;

    function xSwapNative(string memory egressParams, string memory egressAddress) external payable;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                   Egress xSwap with call                 //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function sendxSwapWithCall(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                     Egress xCall                         //
    //                                                          //
    //////////////////////////////////////////////////////////////
    function sendxCall(
        SigData calldata sigData,
        address recipient,
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Governance                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function govWithdraw(address[] calldata tokens) external;

    function enableSwaps() external;

    function disableSwaps() external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getSwapsEnabled() external view returns (bool);
}
