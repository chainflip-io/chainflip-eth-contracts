pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/IStakeManager.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IFLIP.sol";
import "./AggKeyNonceConsumer.sol";
import "./GovernanceCommunityGuarded.sol";

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
 */
contract StakeManager is IStakeManager, AggKeyNonceConsumer, GovernanceCommunityGuarded {
    /// @dev    The FLIP token address. To be set only once after deployment via setFlip.
    // Disable because tokens are usually in caps
    // solhint-disable-next-line var-name-mixedcase
    IFLIP private _FLIP;

    /// @dev    The minimum amount of FLIP needed to stake, to prevent spamming
    uint256 private _minStake;
    /// @dev    Holding pending claims for the 48h withdrawal delay
    mapping(bytes32 => Claim) private _pendingClaims;
    /// @dev   Time after registerClaim required to wait before call to executeClaim
    uint40 public constant CLAIM_DELAY = 2 days;

    /// @dev    The last block number in which the State Chain updated the totalSupply
    uint256 private _lastSupplyUpdateBlockNum = 0;

    // Defined in IStakeManager, just here for convenience
    // struct Claim {
    //     uint256 amount;
    //     address staker;
    //     // 40 so that 160 (from staker) + 40 + 40  + 8 is 256 they can all be packed
    //     // into a single 256 bit slot
    //     uint40 startTime;
    //     uint48 expiryTime;
    //     bool transferIssuer;
    // }

    constructor(IKeyManager keyManager, uint256 minStake) AggKeyNonceConsumer(keyManager) {
        _minStake = minStake;
    }

    /// @dev   Get the governor address from the KeyManager. This is called by the onlyGovernor
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getGovernor() internal view override returns (address) {
        return getKeyManager().getGovernanceKey();
    }

    /// @dev   Get the community key from the KeyManager. This is called by the isCommunityKey
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getCommunityKey() internal view override returns (address) {
        return getKeyManager().getCommunityKey();
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
     *          should be called. Deployed via Deploy.sol so it can't be frontrun. The FLIP
     *          address can only be set once.
     * @param flip FLIP token address
     */
    function setFlip(IFLIP flip) external override nzAddr(address(flip)) {
        require(address(_FLIP) == address(0), "Staking: Flip address already set");
        _FLIP = flip;
        emit FLIPSet(address(flip));
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
        IFLIP flip = _FLIP;
        require(address(flip) != address(0), "Staking: Flip not set");
        require(amount >= _minStake, "Staking: stake too small");
        // Assumption of set token allowance by the user
        flip.transferFrom(msg.sender, address(this), amount);
        emit Staked(nodeID, amount, msg.sender, returnAddr);
    }

    /**
     * @notice  Claim back stake. If only losing an auction, the same amount initially staked
     *          will be sent back. If losing an auction while being a validator,
     *          the amount sent back = stake + rewards - penalties, as determined by the State Chain
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param nodeID    The nodeID of the staker
     * @param amount    The amount of stake to be locked up
     * @param staker    The staker who is to be sent FLIP
     * @param expiryTime   The last valid timestamp that can execute this claim (uint48)
     */
    function registerClaim(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address staker,
        uint40 expiryTime,
        bool transferIssuer
    )
        external
        override
        onlyNotSuspended
        nzBytes32(nodeID)
        nzUint(amount)
        nzAddr(staker)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.registerClaim.selector, nodeID, amount, staker, expiryTime, transferIssuer))
        )
    {
        require(
            // Must be fresh or have been executed & deleted, or past the expiry
            block.timestamp > uint256(_pendingClaims[nodeID].expiryTime),
            "Staking: a pending claim exists"
        );

        uint40 startTime = uint40(block.timestamp) + CLAIM_DELAY;
        require(expiryTime > startTime, "Staking: expiry time too soon");

        _pendingClaims[nodeID] = Claim(amount, staker, startTime, expiryTime, transferIssuer);
        emit ClaimRegistered(nodeID, amount, staker, startTime, expiryTime, transferIssuer);
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
    function executeClaim(bytes32 nodeID) external override onlyNotSuspended {
        Claim memory claim = _pendingClaims[nodeID];
        require(block.timestamp >= claim.startTime && claim.expiryTime > 0, "Staking: early or already execd");

        // Housekeeping
        delete _pendingClaims[nodeID];

        if (block.timestamp <= claim.expiryTime) {
            emit ClaimExecuted(nodeID, claim.amount);

            // Send the tokens
            _FLIP.transfer(claim.staker, claim.amount);

            if (claim.transferIssuer) {
                // Transfer the issuer key to the staker
                // require(IStakeManager(claim.staker).getFLIP() == _FLIP, "Staking: invalid FLIP address");
                _FLIP.updateIssuer(claim.staker);
            }
        } else {
            emit ClaimExpired(nodeID, claim.amount);
        }
    }

    /**
     * @notice      Set the minimum amount of stake needed for `stake` to be able
     *              to be called. Used to prevent spamming of stakes.
     * @param newMinStake   The new minimum stake
     */
    function setMinStake(uint256 newMinStake) external override nzUint(newMinStake) onlyGovernor {
        emit MinStakeChanged(_minStake, newMinStake);
        _minStake = newMinStake;
    }

    /**
     * @notice  Compares a given new FLIP supply against the old supply,
     *          then mints or burns as appropriate. The message must be 
     '          signed by the aggregate key.
     * @param sigData               Struct containing the signature data over the message
     *                              to verify, signed by the aggregate key.
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     * @param account Account of the tokens to be minted/burnt
     */
    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber,
        address account
    )
        external
        override
        nzUint(newTotalSupply)
        nzAddr(account)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.updateFlipSupply.selector, newTotalSupply, stateChainBlockNumber, account))
        )
    {
        // TODO: Should we also add a suspended check? However, we might want to be able to slash nodes when we
        // are in safeMode or this contract is suspended. TBD.
        require(stateChainBlockNumber > _lastSupplyUpdateBlockNum, "Staking: old FLIP supply update");
        _lastSupplyUpdateBlockNum = stateChainBlockNumber;
        IFLIP flip = _FLIP;
        uint256 oldSupply = flip.totalSupply();
        // TODO: Consider having address(this) instead of account to not be able to burn tokens from other addresses.
        // NOTE: If we keep it like this, do we need to check for account != 0? _mint and _burn already do that. TO TEST.
        if (newTotalSupply < oldSupply) {
            uint256 amount = oldSupply - newTotalSupply;
            flip.burn(account, amount);
        } else if (newTotalSupply > oldSupply) {
            uint256 amount = newTotalSupply - oldSupply;
            flip.mint(account, amount);
        }
        emit FlipSupplyUpdated(oldSupply, newTotalSupply, stateChainBlockNumber);
    }

    // NOTE: We could potentially leave this anyway, but in a situation of emergency we will probably pause it
    // and govWithdraw the funds, not sure there is any case where we would want to update the issuer.

    // /**
    //  * @notice  Updates the address that is allowed to mint/burn FLIP tokens. This will be used when the StakeManager
    //  *          contract is upgraded and we need to update the address that is allowed to mint/burn FLIP tokens.
    //  * @param sigData     Struct containing the signature data over the message
    //  *                    to verify, signed by the aggregate key.
    //  * @param newIssuer   New StakeManager contract that will mint/burn FLIP tokens.
    //  */
    // function updateFlipIssuer(
    //     SigData calldata sigData,
    //     address newIssuer
    // )
    //     external
    //     nzAddr(newIssuer)
    //     consumesKeyNonce(sigData, keccak256(abi.encode(this.updateFlipIssuer.selector, newIssuer)))
    // {
    //     // TODO: Should we also add a suspended check? In other contracts, when suspended they can't be upgraded. In this
    //     // case when suspended all claims will expire so we could just do that and upgrade after that. I think it makes
    //     // sense to add the modifier in this case.

    //     // Adding some small safeguard that at least the contract is not an EOA and has a reference to the FLIP contract
    //     // Only downsides are that we have to maintain this getFLIP() on the new contract and that we cannot pass it to
    //     // a multisig. We would need to create a dummy StakeManager contract controlled by the multisig and pass that.
    //     // Otherwise this adds some sanity check. However, we have probably already submitted a claim and executed it,
    //     // so it only prevents a missmatch between the claim and the new contract. That might still be good enough.
    //     IFLIP flip = IStakeManager(newIssuer).getFLIP();
    //     require(flip == _FLIP, "Staking: invalid FLIP address");

    //     _FLIP.updateIssuer(newIssuer);
    // }

    /**
     * @notice Withdraw all FLIP to governance address in case of emergency. This withdrawal needs
     *         to be approved by the Community, it is a last resort. Used to rectify an emergency.
     */
    function govWithdraw() external override onlyGovernor onlyCommunityGuardDisabled onlySuspended {
        uint256 amount = _FLIP.balanceOf(address(this));

        // Could use msg.sender or getGovernor() but hardcoding the get call just for extra safety
        address recipient = getKeyManager().getGovernanceKey();
        _FLIP.transfer(recipient, amount);
        emit GovernanceWithdrawal(recipient, amount);
    }

    /**
     * @notice Withdraw any native tokens on this contract. The intended execution of this contract doesn't
     * require any native tokens. This function is just to recover any native tokens that might have been sent to
     * this contract by accident (or any other reason).
     */
    function govWithdrawNative() external override onlyGovernor {
        uint256 amount = address(this).balance;

        // Could use msg.sender or getGovernor() but hardcoding the get call just for extra safety
        address recipient = getKeyManager().getGovernanceKey();
        payable(recipient).transfer(amount);
        emit GovernanceWithdrawal(recipient, amount);
    }

    /**
     *  @notice Allows this contract to receive native tokens
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
        return _FLIP;
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

    /**
     * @notice  Get the last state chain block number of the last supply update
     * @return  The state chain block number of the last supply update
     */
    function getLastSupplyUpdateBlockNumber() external view override returns (uint256) {
        return _lastSupplyUpdateBlockNum;
    }
}
