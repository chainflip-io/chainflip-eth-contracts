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
        require(cliff_ < end_, "TokenVesting: cliff_ isn't before end_");
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
        uint256 unreleased = _releasableAmount(token);
        require(unreleased > 0, "TokenVesting: no tokens are due");

        released[token] += unreleased;
        token.safeTransfer(beneficiary, unreleased);

        emit TokensReleased(token, unreleased);
    }

    /**
     * @notice Allows the revoker to revoke the vesting. Tokens already vested
     * remain in the contract, the rest are returned to the revoker.
     * @param token ERC20 token which is being vested.
     */
    function revoke(IERC20 token) external {
        require(msg.sender == revoker, "TokenVesting: not the revoker");
        require(revocable, "TokenVesting: cannot revoke");
        require(!revoked[token], "TokenVesting: token already revoked");

        uint balance = token.balanceOf(address(this));

        uint unreleased = _releasableAmount(token);
        uint refund = balance - unreleased;

        revoked[token] = true;

        token.safeTransfer(revoker, refund);

        emit TokenVestingRevoked(token);
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
        uint256 currentBalance = token.balanceOf(address(this));
        uint256 totalBalance = currentBalance + released[token];

        if (block.timestamp < cliff) {
            return 0;
        } else if (block.timestamp >= end || revoked[token]) {
            return totalBalance;
        } else {
            return totalBalance * (block.timestamp - start) / (end - start);
        }
    }
}
