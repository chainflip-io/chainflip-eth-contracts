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
    //                        Swaps                             //
    //                                                          //
    //////////////////////////////////////////////////////////////

    // function swapETH(string calldata egressChainAndToken, bytes32 egressAddress) external payable;

    // function swapToken(
    //     string calldata egressChainAndToken,
    //     bytes32 egressAddress,
    //     IERC20 ingressToken,
    //     uint256 amount
    // ) external;

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
