// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "../abstract/Shared.sol";
import "../interfaces/IStateChainGateway.sol";
import "../interfaces/IAddressHolder.sol";
import "../interfaces/ITokenVestingStaking.sol";
import "../mocks/MockStProvider.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title TokenVestingStaking
 * @dev A token holder contract that that vests its balance of any ERC20 token to the beneficiary.
 *      Validator lockup - stakable. Nothing unlocked until end of contract where everything
 *      unlocks at once. All funds can be staked during the vesting period.
 *      If revoked send all funds to revoker and block beneficiary releases indefinitely.
 *      Any staked funds at the moment of revocation can be retrieved by the revoker upon unstaking.
 *
 *      The reference to the staking contract is hold by the AddressHolder contract to allow for governance to
 *      update it in case the staking contract needs to be upgraded.
 *
 *      The vesting schedule is time-based (i.e. using block timestamps as opposed to e.g. block numbers), and
 *      is therefore sensitive to timestamp manipulation (which is something miners can do, to a certain degree).
 *      Therefore, it is recommended to avoid using short time durations (less than a minute). Typical vesting
 *      schemes, with a cliff period of a year and a duration of four years, are safe to use.
 *
 */
contract TokenVestingStaking is ITokenVestingStaking, Shared {
    using SafeERC20 for IERC20;

    // beneficiary of tokens after they are released. It can be transferrable.
    address private beneficiary;
    bool public immutable transferableBeneficiary;
    // the revoker who can cancel the vesting and withdraw any unvested tokens
    address private revoker;

    // Durations and timestamps are expressed in UNIX time, the same units as block.timestamp.
    uint256 public immutable end;

    // solhint-disable-next-line var-name-mixedcase
    IERC20 public immutable FLIP;

    // The contract that holds the reference addresses for staking purposes.
    IAddressHolder public immutable addressHolder;
    
    bool public revoked;

    // Cumulative counter for amount staked to the st provider
    uint256 public stTokenStaked;

    // Cumulative counter for amount unstaked from the st provider
    uint256 public stTokenUnstaked;

    /**
     * @param beneficiary_ address of the beneficiary to whom vested tokens are transferred
     * @param revoker_   the person with the power to revoke the vesting. Address(0) means it is not revocable.
     * @param end_ the unix time of the end of the vesting period, everything withdrawable after
     * @param transferableBeneficiary_ whether the beneficiary address can be transferred
     * @param addressHolder_ the contract holding the reference address to the ScGateway for staking
     * @param flip_ the FLIP token address.
     */
    constructor(
        address beneficiary_,
        address revoker_,
        uint256 end_,
        bool transferableBeneficiary_,
        IAddressHolder addressHolder_,
        IERC20 flip_
    ) nzAddr(beneficiary_) nzAddr(address(addressHolder_)) nzAddr(address(flip_)) {
        require(end_ > block.timestamp, "Vesting: final time is before current time");

        beneficiary = beneficiary_;
        revoker = revoker_;
        end = end_;
        transferableBeneficiary = transferableBeneficiary_;
        addressHolder = addressHolder_;
        FLIP = flip_;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Funds an account in the statechain with some tokens for the nodeID
     *          and forces the return address of that to be this contract.
     * @param nodeID the nodeID to fund.
     * @param amount the amount of FLIP out of the current funds in this contract.
     */
    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external override onlyBeneficiary notRevoked {
        address stateChainGateway = addressHolder.getStateChainGateway();

        FLIP.approve(stateChainGateway, amount);
        IStateChainGateway(stateChainGateway).fundStateChainAccount(nodeID, amount);
    }

    /**
     * @notice  Stakes to the staking provider by transferring an amount of FLIP to the staking minter.
     *          It is expected that an amount of stFLIP will be minted to this contract.
     * @param amount the amount of FLIP to stake to the staking provider.
     */
    function stakeToStProvider(uint256 amount) external override onlyBeneficiary notRevoked {
        address stMinter = addressHolder.getStakingAddress();

        FLIP.approve(stMinter, amount);
        require(IMinter(stMinter).mint(address(this), amount));

        stTokenStaked += amount;
    }

    /**
     * @notice  Unstakes from the staking provider by transferring stFLIP to the staking burner.
     * @param amount the amount of FLIP to stake to the staking provider.
     */
    function unstakeFromStProvider(uint256 amount) external override onlyBeneficiary notRevoked returns (uint256) {
        (address stBurner, address stFlip) = addressHolder.getUnstakingAddresses();

        IERC20(stFlip).approve(stBurner, amount);

        stTokenUnstaked += amount;

        return IBurner(stBurner).burn(address(this), amount);

    }

    /**
     * @notice Claims the liquid staking provider rewards.
     * @param recipient_ the address to send the rewards to. If 0x0, then the beneficiary is used.
     * @param amount_ the amount of rewards to claim. If greater than `totalRewards`, then all rewards are claimed.
     * @dev `stTokenCounter` updates after staking/unstaking operation to keep track of the st token principle. Any amount above the
     * principle is considered rewards and thus can be claimed by the beneficiary.
     * 
     * Claim rewards flow possibilities
     * 1. increment stake (staked 100, unstaked 0, balance 100)
     * 2. earn rewards    (staked 100, unstaked 0, balance 103)
     * 3. claim rewards   (staked 100, unstaked 0, balance 100) 103 + 0 - 100 = 3
     * 4. receive 3 stflip
     * 
     * 1. stake            (staked 100, unstaked 0, balance 100)
     * 2. earn rewards     (staked 100, unstaked 0, balance 103)
     * 3. unstake all      (staked 100, unstaked 103, balance 0)
     * 4. claim underflows (staked 100, unstaked 103, balance 0) 0 + 103 - 100 = 3
     * 5. Need to have stflip to claim
     * 1. stake            (staked 100, unstaked 0, balance 100)
     * 2. get slashed      (staked 100, unstaked 0, balance 95)
     * 3. unstake all      (staked 100, unstaked 0, balance 95)
     * 4. claim underflows (staked 100, unstaked 0, balance 95) 95 + 0 - 100 = -5
     * 5. must earn 5 stflip first before earning claimable rewards
     * 
     * 1. stake            (staked 100, unstaked 0, balance 100)
     * 2. earn rewards     (staked 100, unstaked 0, balance 103)
     * 3. unstake half     (staked 50, unstaked 53, balance 50)
     * 4. claim rewards   (staked 50, unstaked 53, balance 50) 50 + 53 - 50 = 3
     * 5. Receive 3 stflip
     */
    function claimStProviderRewards(address recipient_, uint256 amount_) external onlyBeneficiary notRevoked {
        (, address stFlip) = addressHolder.getUnstakingAddresses();
        uint256 totalRewards = stFLIP(stFlip).balanceOf(address(this)) + stTokenUnstaked - stTokenStaked;

        uint256 amount = amount_ > totalRewards ? totalRewards : amount_;
        address recipient = recipient_ == address(0) ? beneficiary : recipient_;

        stFLIP(stFlip).transfer(recipient, amount);
    }

    /**
     * @notice Transfers vested tokens to beneficiary.
     * @param token ERC20 token which is being vested.
     */
    function release(IERC20 token) external override onlyBeneficiary notRevoked {
        uint256 unreleased = _releasableAmount(token);
        require(unreleased > 0, "Vesting: no tokens are due");

        emit TokensReleased(token, unreleased);

        token.safeTransfer(beneficiary, unreleased);
    }

    /**
     * @notice Allows the revoker to revoke the vesting and stop the beneficiary from releasing
     * any tokens if the vesting period has not bene completed. Any staked tokens at the time of
     * revoking can be retrieved by the revoker upon unstaking via `retrieveRevokedFunds`.
     * @param token ERC20 token which is being vested.
     */
    function revoke(IERC20 token) external override onlyRevoker notRevoked {
        require(block.timestamp <= end, "Vesting: vesting expired");

        uint256 balance = token.balanceOf(address(this));

        uint256 unreleased = _releasableAmount(token);
        uint256 refund = balance - unreleased;

        revoked = true;

        token.safeTransfer(revoker, refund);

        emit TokenVestingRevoked(token, refund);
    }

    /**
     * @notice Allows the revoker to retrieve tokens that have been unstaked after the revoke
     *         function has been called. Safeguard mechanism in case of unstaking happening
     *         after revoke, otherwise funds would be locked.
     * @param token ERC20 token which is being vested.
     */
    function retrieveRevokedFunds(IERC20 token) external override onlyRevoker {
        require(revoked, "Vesting: token not revoked");
        uint256 balance = token.balanceOf(address(this));

        token.safeTransfer(revoker, balance);
    }

    /**
     * @dev Calculates the amount that has already vested but hasn't been released yet.
     * @param token ERC20 token which is being vested.
     */
    function _releasableAmount(IERC20 token) private view returns (uint256) {
        return block.timestamp < end ? 0 : token.balanceOf(address(this));
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

    modifier notRevoked() {
        require(!revoked, "Vesting: token revoked");
        _;
    }
}
