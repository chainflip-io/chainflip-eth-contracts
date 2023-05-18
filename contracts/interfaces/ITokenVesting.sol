pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface ITokenVesting {
    event TokensReleased(IERC20 indexed token, uint256 amount);
    event TokenVestingRevoked(IERC20 indexed token, uint256 refund);

    event BeneficiaryUpdated(address oldBeneficiary, address newBeneficiary);
    event RevokerUpdated(address oldRevoker, address newRevoker);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external;

    function release(IERC20 token) external;

    function revoke(IERC20 token) external;

    function retrieveRevokedFunds(IERC20 token) external;

    function updateBeneficiary(address beneficiary_) external;

    function updateRevoker(address revoker_) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getBeneficiary() external view returns (address);

    function getRevoker() external view returns (address);
}
