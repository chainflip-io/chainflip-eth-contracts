pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./IAggKeyNonceConsumer.sol";
import "./IGovernanceCommunityGuarded.sol";

/**
 * @title    Vault interface
 * @notice   The interface for functions Vault implements
 * @author   Quantaf1re (James Key)
 */
interface IVault is IGovernanceCommunityGuarded, IAggKeyNonceConsumer {
    function allBatch(
        SigData calldata sigData,
        bytes32[] calldata fetchSwapIDs,
        IERC20[] calldata fetchTokens,
        IERC20[] calldata tranTokens,
        address payable[] calldata tranRecipients,
        uint256[] calldata tranAmounts
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Transfers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function transfer(
        SigData calldata sigData,
        IERC20 token,
        address payable recipient,
        uint256 amount
    ) external;

    function transferBatch(
        SigData calldata sigData,
        IERC20[] calldata tokens,
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Fetch Deposits                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function fetchDepositEth(SigData calldata sigData, bytes32 swapID) external;

    function fetchDepositEthBatch(SigData calldata sigData, bytes32[] calldata swapIDs) external;

    function fetchDepositToken(
        SigData calldata sigData,
        bytes32 swapID,
        IERC20 token
    ) external;

    function fetchDepositTokenBatch(
        SigData calldata sigData,
        bytes32[] calldata swapIDs,
        IERC20[] calldata tokens
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Swaps                             //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function swapETH(
        uint256 egressChainID,
        string calldata egressToken,
        bytes32 egressAddress
    ) external payable;

    function swapToken(
        uint256 egressChainID,
        string calldata egressToken,
        bytes32 egressAddress,
        uint256 amount
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Governance                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function govWithdraw(IERC20[] calldata tokens) external;

    function enableSwaps() external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getSwapsEnabled() external view returns (bool);
}
