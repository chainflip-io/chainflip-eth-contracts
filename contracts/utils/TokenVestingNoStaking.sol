// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../abstract/Shared.sol";
import "../interfaces/ITokenVestingNoStaking.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title TokenVesting
 * @dev A token holder contract that that vests its balance of any ERC20 token to the beneficiary.
 *      Linear lockup - not stakable. 20% cliff unlocking and 80% linear after that.
 *      If revoked send all funds to revoker and allow beneficiary to release remaining vested funds.
 *
 *      The vesting schedule is time-based (i.e. using block timestamps as opposed to e.g. block numbers), and
 *      is therefore sensitive to timestamp manipulation (which is something miners can do, to a certain degree).
 *      Therefore, it is recommended to avoid using short time durations (less than a minute).
 *
 */
contract TokenVestingNoStaking is ITokenVestingNoStaking, Shared {
    using SafeERC20 for IERC20;

    uint256 public constant CLIFF_DENOMINATOR = 5; // x / 5 = 20% of x

    // beneficiary of tokens after they are released. It can be transferrable.
    address private beneficiary;
    bool public immutable transferableBeneficiary;
    // the revoker who can cancel the vesting and withdraw any unvested tokens
    address private revoker;

    // Durations and timestamps are expressed in UNIX time, the same units as block.timestamp.
    uint256 public immutable cliff;
    uint256 public immutable end;

    mapping(IERC20 => uint256) public released;
    bool public revoked;

    /**
     * @param beneficiary_ address of the beneficiary to whom vested tokens are transferred
     * @param revoker_   the person with the power to revoke the vesting. Address(0) means it is not revocable.
     * @param cliff_ the unix time of the cliff, nothing withdrawable before this
     * @param end_ the unix time of the end of the vesting period, everything withdrawable after
     * @param transferableBeneficiary_ whether the beneficiary address can be transferred
     */
    constructor(
        address beneficiary_,
        address revoker_,
        uint256 cliff_,
        uint256 end_,
        bool transferableBeneficiary_
    ) nzAddr(beneficiary_) {
        require(cliff_ <= end_, "Vesting: cliff_ after end_");
        require(block.timestamp < cliff_, "Vesting: cliff before current time");

        beneficiary = beneficiary_;
        revoker = revoker_;
        cliff = cliff_;
        end = end_;
        transferableBeneficiary = transferableBeneficiary_;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice Transfers vested tokens to beneficiary.
     * @param token ERC20 token which is being vested.
     */
    function release(IERC20 token) external override onlyBeneficiary {
        uint256 unreleased = _releasableAmount(token);
        require(unreleased > 0, "Vesting: no tokens are due");

        released[token] += unreleased;
        emit TokensReleased(token, unreleased);

        token.safeTransfer(beneficiary, unreleased);
    }

    /**
     * @notice Allows the revoker to revoke the vesting. Tokens already vested remain
     *         in the contract for the beneficiary to release, the rest are returned
     *         to the revoker.
     * @param token ERC20 token which is being vested.
     */
    function revoke(IERC20 token) external override onlyRevoker {
        require(!revoked, "Vesting: token revoked");
        require(block.timestamp <= end, "Vesting: vesting expired");

        uint256 balance = token.balanceOf(address(this));

        uint256 unreleased = _releasableAmount(token);
        uint256 refund = balance - unreleased;

        revoked = true;

        token.safeTransfer(revoker, refund);

        emit TokenVestingRevoked(token, refund);
    }

    /**
     * @dev Calculates the amount that has already vested but hasn't been released yet.
     * @param token ERC20 token which is being vested.
     */
    function _releasableAmount(IERC20 token) private view returns (uint256) {
        return _vestedAmount(token) - released[token];
    }

    /**
     * @dev Calculates the amount that has already vested.
     * @param token ERC20 token which is being vested.
     */
    function _vestedAmount(IERC20 token) private view returns (uint256) {
        if (block.timestamp < cliff) {
            return 0;
        }
        uint256 currentBalance = token.balanceOf(address(this));
        uint256 totalBalance = currentBalance + released[token];

        if (block.timestamp >= end || revoked) {
            return totalBalance;
        } else {
            uint256 cliffAmount = totalBalance / CLIFF_DENOMINATOR;
            return cliffAmount + ((totalBalance - cliffAmount) * (block.timestamp - cliff)) / (end - cliff);
        }
    }

    /// @dev    Allow the beneficiary to be transferred to a new address if needed
    function transferBeneficiary(address beneficiary_) external override onlyBeneficiary nzAddr(beneficiary_) {
        require(transferableBeneficiary, "Vesting: beneficiary not transferrable");
        emit BeneficiaryTransferred(beneficiary, beneficiary_);
        beneficiary = beneficiary_;
    }

    /// @dev    Allow the revoker to be transferred to a new address if needed
    function transferRevoker(address revoker_) external override onlyRevoker nzAddr(revoker_) {
        emit RevokerTransferred(revoker, revoker_);
        revoker = revoker_;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                Non-state-changing functions              //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @return the beneficiary address
     */
    function getBeneficiary() external view override returns (address) {
        return beneficiary;
    }

    /**
     * @return the revoker address
     */
    function getRevoker() external view override returns (address) {
        return revoker;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                      Modifiers                           //
    //                                                          //
    //////////////////////////////////////////////////////////////
    /**
     * @dev Ensure that the caller is the beneficiary address
     */
    modifier onlyBeneficiary() {
        require(msg.sender == beneficiary, "Vesting: not the beneficiary");
        _;
    }

    /**
     * @dev Ensure that the caller is the revoker address
     */
    modifier onlyRevoker() {
        require(msg.sender == revoker, "Vesting: not the revoker");
        _;
    }
}
