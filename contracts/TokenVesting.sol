pragma solidity ^0.8.0;


import "./interfaces/IStakeManager.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";


/**
 * @title TokenVesting
 * @dev A token holder contract that can release its token balance gradually like a
 * typical vesting scheme, with a cliff and vesting period. Optionally revocable by the
 * owner.
 */
contract TokenVesting is ReentrancyGuard {
    // The vesting schedule is time-based (i.e. using block timestamps as opposed to e.g. block numbers), and is
    // therefore sensitive to timestamp manipulation (which is something miners can do, to a certain degree). Therefore,
    // it is recommended to avoid using short time durations (less than a minute). Typical vesting schemes, with a
    // cliff period of a year and a duration of four years, are safe to use.
    // solhint-disable not-rely-on-time

    using SafeERC20 for IERC20;

    event TokensReleased(IERC20 indexed token, uint256 amount);
    event TokenVestingRevoked(IERC20 indexed token);

    // beneficiary of tokens after they are released
    address public beneficiary;
    // the revoker who can cancel cancel the vesting and withdraw any unvested tokens
    address public revoker;
    // whether the revoker can revoke and withdraw unvested tokens
    bool public revocable;

    // Durations and timestamps are expressed in UNIX time, the same units as block.timestamp.
    uint public start;
    uint public cliff;
    uint public end;

    // If false, staking is not allowed
    bool public canStake;
    // The staking contract to stake to if `canStake`
    IStakeManager public stakeManager;

    mapping (IERC20 => uint256) public released;
    mapping (IERC20 => bool) public revoked;

    /**
     * @dev Creates a vesting contract that vests its balance of any ERC20 token to the
     * beneficiary, gradually in a linear fashion until `end`. By then all
     * of the balance will have vested.
     * @param beneficiary_ address of the beneficiary to whom vested tokens are transferred
     * @param revoker_   the person with the power to rug the vesting
     * @param revocable_ whether the vesting is revocable or not
     * @param start_ the unix time to start the vesting calculation at
     * @param cliff_ the unix time of the cliff, nothing withdrawable before this
     * @param end_ the unix time of the end of the vesting period, everything withdrawable after
     * @param canStake_ whether the investor is allowed to use vested funds to stake
     * @param stakeManager_ the staking contract to stake to if canStake
     */
    constructor (
        address beneficiary_,
        address revoker_,
        bool revocable_,
        uint start_,
        uint cliff_,
        uint end_,
        bool canStake_,
        IStakeManager stakeManager_
    ) {
        require(beneficiary_ != address(0), "TokenVesting: beneficiary_ is the zero address");
        require(revoker_ != address(0), "TokenVesting: revoker_ is the zero address");
        require(start_ > 0, "TokenVesting: start_ is 0");
        // solhint-disable-next-line max-line-length
        require(start_ < cliff_, "TokenVesting: start_ isn't before cliff_");
        require(cliff_ <= end_, "TokenVesting: cliff_ isn't before end_");
        // solhint-disable-next-line max-line-length
        require(end_ > block.timestamp, "TokenVesting: final time is before current time");
        require(address(stakeManager_) != address(0), "TokenVesting: stakeManager_ is the zero address");

        beneficiary = beneficiary_;
        revoker = revoker_;
        revocable = revocable_;
        start = start_;
        cliff = cliff_;
        end = end_;
        canStake = canStake_;
        //Add require (or assign) cliff = end when canStake?
        stakeManager = stakeManager_;
    }

    /**
     * @notice  stakes some tokens for the nodeID and forces the return
     *          address of that stake to be this contract.
     * @param nodeID the nodeID to stake for.
     * @param amount the amount to stake out of the current funds in this contract.
     */
    function stake(bytes32 nodeID, uint amount) external {
        require(msg.sender == beneficiary, "TokenVesting: not the beneficiary");
        require(canStake, "TokenVesting: cannot stake");

        stakeManager.stake(nodeID, amount, address(this));
    }

    /**
     * @notice Transfers vested tokens to beneficiary.
     * @param token ERC20 token which is being vested.
     */
    function release(IERC20 token) external nonReentrant {
        require (!canStake || !revoked[token], "TokenVesting: staked funds revoked");
        uint256 unreleased = _releasableAmount(token);
        require(unreleased > 0, "TokenVesting: no tokens are due");

        released[token] += unreleased;
        token.safeTransfer(beneficiary, unreleased);

        emit TokensReleased(token, unreleased);
    }
    

    /**
     * @notice Allows the revoker to revoke the vesting. Tokens already vested
     *         remain in the contract, the rest are returned to the revoker.
     *         Assumption is made that revoked will be called once funds are unstaked
     *         and sent back to this contract.
     * @param token ERC20 token which is being vested.
     */
    function revoke(IERC20 token) external {
        require(msg.sender == revoker, "TokenVesting: not the revoker");
        require(revocable, "TokenVesting: cannot revoke");
        require(!revoked[token], "TokenVesting: token already revoked");
        require(block.timestamp <= end , "TokenVesting: vesting period expired");

        uint balance = token.balanceOf(address(this));

        uint unreleased = _releasableAmount(token);
        uint refund = balance - unreleased;

        revoked[token] = true;

        token.safeTransfer(revoker, refund);

        emit TokenVestingRevoked(token);
    }

    /**
     * @notice Allows the revoker to retrieve tokens that have been unstaked after
     *         the revoke function has been called (in canStake contracts)
     *         This is in case the staker doesn't agree to unstake in time and the funds
     *         are not in this contract when revoked is called.
     *         In !canStake contracts all the funds are withdrawn once revoked is called
     * @param token ERC20 token which is being vested.
     */
    function retrieveRevokedFunds (IERC20 token) external {
        require(msg.sender == revoker, "TokenVesting: not the revoker");
        require(revocable, "TokenVesting: cannot revoke");
        require(revoked[token], "TokenVesting: token not revoked");  

        require(canStake, "TokenVesting: not retrievable");

        uint balance = token.balanceOf(address(this));

        token.safeTransfer(revoker, balance);
    }

    /**
     * @dev Calculates the amount that has already vested but hasn't been released yet.
     * @param token ERC20 token which is being vested.
     */
    function _releasableAmount(IERC20 token) private view returns (uint) {
        return _vestedAmount(token) - released[token];
    }

    /**
     * @dev Calculates the amount that has already vested.
     * @param token ERC20 token which is being vested.
     */
    function _vestedAmount(IERC20 token) private view returns (uint) {
        
        // We assume all the funds are in the contract and/or relased
        // Either because the contract is option B or because
        // all the tokens have been unstaked when revoking.
        uint256 currentBalance = token.balanceOf(address(this));
        uint256 totalBalance = currentBalance + released[token];

        if (block.timestamp < cliff) {
            return 0;
        } else if (block.timestamp >= end || revoked[token]) {
            // Any amount that is in the contract
            // we can only get here through revoked[token] if we are revoking or if we are releasing and !canstake
            return totalBalance;
        } else {
            assert (!canStake);
            // we should never enter this if canStake == true, since cliff == end in the constructor. Add an assert?
            // This might need to be modified if we add a getRewards functionality for stakers.
            uint256 cliffAmount = totalBalance / 5;
            return cliffAmount + (totalBalance - cliffAmount)  * (block.timestamp - cliff) / (end - cliff);
        }
    }
}
