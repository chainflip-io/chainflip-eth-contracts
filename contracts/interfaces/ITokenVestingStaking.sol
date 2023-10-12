// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface ITokenVestingStaking {
    event TokensReleased(IERC20 indexed token, uint256 amount);
    event TokenVestingRevoked(IERC20 indexed token, uint256 refund);

    event BeneficiaryTransferred(address oldBeneficiary, address newBeneficiary);
    event RevokerTransferred(address oldRevoker, address newRevoker);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external;

    function stakeToStProvider(uint256 amount) external;

    function unstakeFromStProvider(uint256 amount) external returns (uint256);

    function claimStProviderRewards(uint256 amount_) external;

    function release(IERC20 token) external;

    function revoke(IERC20 token) external;

    function retrieveRevokedFunds(IERC20 token) external;

    function transferBeneficiary(address beneficiary_) external;

    function transferRevoker(address revoker_) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getBeneficiary() external view returns (address);

    function getRevoker() external view returns (address);
}
