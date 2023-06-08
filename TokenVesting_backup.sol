// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./interfaces/IStateChainGateway.sol";
import "./interfaces/IAddressHolder.sol";
import "./interfaces/ITokenVesting.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface Minter {
    function mint(address to, uint256 amount) external returns (bool);
}

interface Burner {
    function burn(address to, uint256 amount) external returns (uint256);

    function stFlip() external returns (address);
}

/**
 * @title TokenVesting
 * @dev A token holder contract that that vests its balance of any ERC20 token to the beneficiary.
 *      Two vesting contract options:
 *        Option A: Validator lockup - stakable. Nothing unlocked until end of contract where everything
 *                  unlocks at once. All funds can be staked during the vesting period.
 *                  If revoked send all funds to revoker and block beneficiary releases indefinitely.
 *                  Any staked funds at the moment of revocation can be retrieved by the revoker upon unstaking.
 *        Option B: Linear lockup - not stakable. 20% cliff unlocking and 80% linear after that.
 *                  If revoked send all funds to revoker and allow beneficiary to release remaining vested funds.
 *
 *       The reference to the staking contract is hold by the AddressHolder contract to allow for governance to
 *       update it in case the staking contract needs to be upgraded.
 *
 *       The vesting schedule is time-based (i.e. using block timestamps as opposed to e.g. block numbers), and
 *       is therefore sensitive to timestamp manipulation (which is something miners can do, to a certain degree).
 *       Therefore, it is recommended to avoid using short time durations (less than a minute). Typical vesting
 *       schemes, with a cliff period of a year and a duration of four years, are safe to use.
 *
 */
contract TokenVesting is ITokenVesting {
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

    // If false, staking is not allowed
    bool public immutable canStake;
    // The contract that holds the reference to the staking contract. Only relevant if `canStake`
    IAddressHolder public immutable scGatewayAddrHolder;

    // Liquidity Staking protocol addresses
    Minter public immutable minter;
    Burner public immutable burner;

    mapping(IERC20 => uint256) public released;
    mapping(IERC20 => bool) public revoked;

    /**
     * @param beneficiary_ address of the beneficiary to whom vested tokens are transferred
     * @param revoker_   the person with the power to revoke the vesting. Address(0) means it is not revocable.
     * @param cliff_ the unix time of the cliff, nothing withdrawable before this
     * @param end_ the unix time of the end of the vesting period, everything withdrawable after
     * @param canStake_ whether the investor is allowed to use vested funds to stake
     * @param transferableBeneficiary_ whether the beneficiary address can be transferred
     * @param scGatewayAddrHolder_ the contract holding the reference address to the ScGateway to if `canStake`
     */
    constructor(
        address beneficiary_,
        address revoker_,
        uint256 cliff_,
        uint256 end_,
        bool canStake_,
        bool transferableBeneficiary_,
        IAddressHolder scGatewayAddrHolder_,
        Minter minter_,
        Burner burner_
    ) {
        require(beneficiary_ != address(0), "Vesting: beneficiary_ is the zero address");
        require(cliff_ <= end_, "Vesting: cliff_ after end_");
        require(end_ > block.timestamp, "Vesting: final time is before current time");
        require(address(scGatewayAddrHolder_) != address(0), "Vesting: addrHolder is the zero address");
        if (canStake_) require(cliff_ == end_, "Vesting: invalid staking contract cliff");

        beneficiary = beneficiary_;
        revoker = revoker_;
        cliff = cliff_;
        end = end_;
        canStake = canStake_;
        transferableBeneficiary = transferableBeneficiary_;
        scGatewayAddrHolder = scGatewayAddrHolder_;
        // Setting these two zero will basically make it not stakable via LSP
        minter = minter_;
        burner = burner_;
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
    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external override onlyBeneficiary {
        require(canStake, "Vesting: cannot stake");
        IStateChainGateway stateChainGateway = IStateChainGateway(scGatewayAddrHolder.getReferenceAddress());

        IERC20 flip = stateChainGateway.getFLIP();
        require(!revoked[flip], "Vesting: FLIP revoked");

        flip.approve(address(stateChainGateway), amount);
        stateChainGateway.fundStateChainAccount(nodeID, amount);
    }

    /**
     * @notice  Stake via Staking provider by providing FLIP to min stFLIP
     * @param amount the amount of FLIP out of the current funds in this contract.
     */
    function stakeViaStakingProvider(uint256 amount) external onlyBeneficiary {
        require(canStake, "Vesting: cannot stake");

        IERC20 flip = IStateChainGateway(scGatewayAddrHolder.getReferenceAddress()).getFLIP();
        require(!revoked[flip], "Vesting: FLIP revoked");

        flip.approve(address(minter), amount);
        minter.mint(address(this), amount);
    }

    function unstakeFromStakingProvider(uint256 amount) external onlyBeneficiary {
        require(canStake, "Vesting: cannot stake");

        IERC20 stFlip = IERC20(burner.stFlip());
        require(!revoked[stFlip], "Vesting: FLIP revoked");

        stFlip.approve(address(burner), amount);
        burner.burn(address(this), amount);
    }

    /**
     * @notice Transfers vested tokens to beneficiary.
     * @param token ERC20 token which is being vested.
     */
    function release(IERC20 token) external override onlyBeneficiary {
        require(!canStake || !revoked[token], "Vesting: staked funds revoked");

        uint256 unreleased = _releasableAmount(token);
        require(unreleased > 0, "Vesting: no tokens are due");

        released[token] += unreleased;
        emit TokensReleased(token, unreleased);

        token.safeTransfer(beneficiary, unreleased);
    }

    /**
     * @notice Allows the revoker to revoke the vesting.
     *         When nonstakable, Tokens already vested remain in the contract
     *         for the beneficiary to release, the rest are returned to the revoker.
     *         When stakable, assumption is made that revoked will be called once
     *         funds are unstaked and sent back to this contract.
     * @param token ERC20 token which is being vested.
     */
    function revoke(IERC20 token) external override onlyRevoker {
        require(!revoked[token], "Vesting: token already revoked");
        require(block.timestamp <= end, "Vesting: vesting expired");

        uint256 balance = token.balanceOf(address(this));

        uint256 unreleased = _releasableAmount(token);
        uint256 refund = balance - unreleased;

        revoked[token] = true;

        token.safeTransfer(revoker, refund);

        emit TokenVestingRevoked(token, refund);
    }

    /**
     * @notice Allows the revoker to retrieve tokens that have been unstaked
     *         after the revoke function has been called (iff `canStake`).
     *         Safeguard mechanism in case of unstaking happening after revoke.
     *         Otherwise funds would be locked. In !canStake contracts all the
     *         funds are withdrawn once revoked is called, so no need for this
     * @param token ERC20 token which is being vested.
     */
    function retrieveRevokedFunds(IERC20 token) external override onlyRevoker {
        require(revoked[token], "Vesting: token not revoked");

        // Prevent revoker from withdrawing vested funds that belong to the beneficiary
        require(canStake, "Vesting: not retrievable");

        uint256 balance = token.balanceOf(address(this));

        token.safeTransfer(revoker, balance);
    }

    /**
     * @dev Calculates the amount that has already vested but hasn't been released yet.
     * @param token ERC20 token which is being vested.
     */
    function _releasableAmount(IERC20 token) private view returns (uint256) {
        return _vestedAmount(token) - released[token];
    }

    /**
     * @dev Calculates the amount that has already vested. Linear unvesting for
     *      option A, full unvesting at the end for contract B.
     * @param token ERC20 token which is being vested.
     */
    function _vestedAmount(IERC20 token) private view returns (uint256) {
        if (block.timestamp < cliff) {
            return 0;
        }
        uint256 currentBalance = token.balanceOf(address(this));
        uint256 totalBalance = currentBalance + released[token];

        if (block.timestamp >= end || revoked[token]) {
            return totalBalance;
        } else {
            // should never enter this if canStake == true, since cliff == end
            assert(!canStake);
            uint256 cliffAmount = totalBalance / CLIFF_DENOMINATOR;
            return cliffAmount + ((totalBalance - cliffAmount) * (block.timestamp - cliff)) / (end - cliff);
        }
    }

    /// @dev    Allow the beneficiary to be transferred to a new address if needed
    function transferBeneficiary(address beneficiary_) external override onlyBeneficiary {
        require(beneficiary_ != address(0), "Vesting: beneficiary_ is the zero address");
        require(transferableBeneficiary, "Vesting: beneficiary not transferrable");
        emit BeneficiaryTransferred(beneficiary, beneficiary_);
        beneficiary = beneficiary_;
    }

    /// @dev    Allow the revoker to be transferred to a new address if needed
    function transferRevoker(address revoker_) external override onlyRevoker {
        require(revoker_ != address(0), "Vesting: revoker_ is the zero address");
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
