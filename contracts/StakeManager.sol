pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "./interfaces/IStakeManager.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IFLIP.sol";
import "./FLIP.sol";
import "./AggKeyNonceConsumer.sol";
import "./CommunityOverriden.sol";

/**
 * @title    StakeManager contract
 * @notice   Manages the staking of FLIP. Validators on the FLIP state chain
 *           basically have full control of FLIP leaving the contract. Bidders
 *           send their bid to this contract via `stake` with their state chain
 *           nodeID.
 *
 *           This contract also handles the minting and burning of FLIP after the
 *           initial supply is minted during FLIP's creation. At any time, a
 *           valid aggragate signature can be submitted to the contract which
 *           updates the total supply by minting or burning the necessary FLIP.
 * @author   Quantaf1re (James Key)
 */
contract StakeManager is IStakeManager, AggKeyNonceConsumer, CommunityOverriden, ReentrancyGuard {
    /// @dev    The FLIP token. Initial value to be set using updateFLIP
    // Disable because tokens are usually in caps
    // solhint-disable-next-line var-name-mixedcase
    FLIP private _FLIP;

    /// @dev    Whether execution of claims is suspended. Used in emergencies.
    bool public suspended = false;

    /// @dev    The minimum amount of FLIP needed to stake, to prevent spamming
    uint256 private _minStake;
    /// @dev    Holding pending claims for the 48h withdrawal delay
    mapping(bytes32 => Claim) private _pendingClaims;
    /// @dev   Time after registerClaim required to wait before call to executeClaim
    uint48 public constant CLAIM_DELAY = 2 days;
    /// @dev   Deployer address that can call setFlip
    address private immutable deployer;

    // Defined in IStakeManager, just here for convenience
    // struct Claim {
    //     uint amount;
    //     address staker;
    //     // 48 so that 160 (from staker) + 48 + 48 is 256 they can all be packed
    //     // into a single 256 bit slot
    //     uint48 startTime;
    //     uint48 expiryTime;
    // }

    constructor(
        IKeyManager keyManager,
        uint256 minStake,
        address communityKey
    ) AggKeyNonceConsumer(keyManager) CommunityOverriden(communityKey) {
        _minStake = minStake;
        deployer = msg.sender;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Sets the FLIP address after initialization. We can't do this in the constructor
     *          because FLIP contract requires this contract's address on deployment for minting.
     *          First this contract is deployed, then the FLIP contract and finally setFLIP
     *          should be called. OnlyDeployer modifer for added security since tokens will be
     *          minted to this contract before calling setFLIP.
     * @param flip FLIP token address
     */
    function setFlip(FLIP flip) external onlyDeployer nzAddr(address(flip)) {
        require(address(_FLIP) == address(0), "Staking: Flip address already set");
        _FLIP = flip;
    }

    /**
     * @notice          Stake some FLIP and attribute it to a nodeID
     * @dev             Requires the staker to have called `approve` in FLIP
     * @param amount    The amount of stake to be locked up
     * @param nodeID    The nodeID of the staker
     * @param returnAddr    The address which the staker requires to be used
     *                      when claiming back FLIP for `nodeID`
     */
    function stake(
        bytes32 nodeID,
        uint256 amount,
        address returnAddr
    ) external override nzBytes32(nodeID) nzAddr(returnAddr) {
        require(amount >= _minStake, "Staking: stake too small");
        // Assumption of set token allowance by the user
        _FLIP.transferFrom(msg.sender, address(this), amount);
        emit Staked(nodeID, amount, msg.sender, returnAddr);
    }

    /**
     * @notice  Claim back stake. If only losing an auction, the same amount initially staked
     *          will be sent back. If losing an auction while being a validator,
     *          the amount sent back = stake + rewards - penalties, as determined by the State Chain
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint)
     * @param nodeID    The nodeID of the staker
     * @param amount    The amount of stake to be locked up
     * @param staker    The staker who is to be sent FLIP
     * @param expiryTime   The last valid block height that can execute this claim (uint48)
     */
    function registerClaim(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address staker,
        uint48 expiryTime
    )
        external
        override
        nonReentrant
        nzBytes32(nodeID)
        nzUint(amount)
        nzAddr(staker)
        consumerKeyNonce(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.registerClaim.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    nodeID,
                    amount,
                    staker,
                    expiryTime
                )
            )
        )
    {
        require(
            // Must be fresh or have been executed & deleted, or past the expiry
            block.timestamp > uint256(_pendingClaims[nodeID].expiryTime),
            "Staking: a pending claim exists"
        );

        uint48 startTime = uint48(block.timestamp) + CLAIM_DELAY;
        require(expiryTime > startTime, "Staking: expiry time too soon");

        _pendingClaims[nodeID] = Claim(amount, staker, startTime, expiryTime);
        emit ClaimRegistered(nodeID, amount, staker, startTime, expiryTime);
    }

    /**
     * @notice  Execute a pending claim to get back stake. If only losing an auction,
     *          the same amount initially staked will be sent back. If losing an
     *          auction while being a validator, the amount sent back = stake +
     *          rewards - penalties, as determined by the State Chain. Cannot execute a pending
     *          claim before 48h have passed after registering it, or after the specified
     *          expiry time
     * @dev     No need for nzUint(nodeID) since that is handled by
     *          `uint(block.number) <= claim.startTime`
     * @param nodeID    The nodeID of the staker
     */
    function executeClaim(bytes32 nodeID) external override {
        require(!suspended, "Staking: suspended");
        Claim memory claim = _pendingClaims[nodeID];
        require(
            uint256(block.timestamp) >= claim.startTime && uint256(block.timestamp) <= claim.expiryTime,
            "Staking: early, late, or execd"
        );

        // Housekeeping
        delete _pendingClaims[nodeID];
        emit ClaimExecuted(nodeID, claim.amount);

        // Send the tokens
        _FLIP.transfer(claim.staker, claim.amount);
    }

    /**
     * @notice      Set the minimum amount of stake needed for `stake` to be able
     *              to be called. Used to prevent spamming of stakes.
     * @param newMinStake   The new minimum stake
     */
    function setMinStake(uint256 newMinStake) external override nzUint(newMinStake) isGovernor {
        emit MinStakeChanged(_minStake, newMinStake);
        _minStake = newMinStake;
    }

    /**
     * @notice Can be used to suspend executions of claims - only executable by
     * governance and should only be used if fraudulent claim is suspected.
     */
    function suspend() external override isGovernor {
        suspended = true;
    }

    /**
     * @notice Can be used by governance to resume the execution of claims.
     */
    function resume() external override isGovernor {
        suspended = false;
    }

    /**
     * @notice Withdraw all FLIP to governance address in case of emergency. This withdrawal needs
     *         to be approved by the Community, it is a last resort. Used to rectify an emergency.
     */
    function govWithdraw() external override isGovernor isNotCommunityOverriden {
        require(suspended, "Staking: Not suspended");
        uint256 amount = _FLIP.balanceOf(address(this));

        // msg.sender == Governor address
        _FLIP.transfer(msg.sender, amount);
        emit GovernanceWithdrawal(msg.sender, amount);
    }

    /**
     *  @notice Allows this contract to receive ETH used to refund callers
     */
    receive() external payable {}

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the FLIP token address
     * @return  The address of FLIP
     */
    function getFLIP() external view override returns (IFLIP) {
        return IFLIP(address(_FLIP));
    }

    /**
     * @notice  Get the minimum amount of stake that's required for a bid
     *          attempt in the auction to be valid - used to prevent sybil attacks
     * @return  The minimum stake (uint)
     */
    function getMinimumStake() external view override returns (uint256) {
        return _minStake;
    }

    /**
     * @notice  Get the pending claim for the input nodeID. If there was never
     *          a pending claim for this nodeID, or it has already been executed
     *          (and therefore deleted), it'll return (0, 0x00..., 0, 0)
     * @return  The claim (Claim)
     */
    function getPendingClaim(bytes32 nodeID) external view override returns (Claim memory) {
        return _pendingClaims[nodeID];
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @notice Ensure that the caller is the KeyManager's governor address.
    modifier isGovernor() {
        require(msg.sender == _getKeyManager().getGovernanceKey(), "Staking: not governor");
        _;
    }

    /// @notice Ensure that the caller is the deployer address.
    modifier onlyDeployer() {
        require(msg.sender == deployer, "Staking: not deployer");
        _;
    }
}
