pragma solidity ^0.8.0;

import "./interfaces/IStakeManager.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IFLIP.sol";
import "./abstract/Shared.sol";
import "./FLIP.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

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
contract StakeManager is Shared, IStakeManager, ReentrancyGuard {
    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;
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
        FLIP flip
    ) {
        _minStake = minStake;
        _keyManager = keyManager;
        // PROBLEM: StakeManager requires FLIP on constructor and FLIP requires reciever (StakeManager) on constructor
        // Add a one-time callable function to set FLIP after constructor? or a keyManager gated update FLIP function?
        _FLIP = flip;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

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
        require(_FLIP.transferFrom(msg.sender, address(this), amount));
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
        updatedValidSig(
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
        require(_FLIP.transfer(claim.staker, claim.amount));
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
     * @notice In the event of fraudulent claims being accepted, the contract is
     * effectively useless. This function allows governance to admit that by
     * withdrawing all the FLIP to their address. From where it will be dealt
     * with later.
     */
    function govWithdraw() external override isGovernor {
        require(suspended, "Staking: Not suspended");
        address to = _keyManager.getGovernanceKey();
        uint256 amount = _FLIP.balanceOf(address(this));
        require(_FLIP.transfer(to, amount));
        emit GovernanceWithdrawal(to, amount);
    }

    /**
     * @notice  Update KeyManager reference. Used if KeyManager contract is updated
     * @param sigData   The keccak256 hash over the msg (uint) (here that's normally
     *                  a hash over the calldata to the function with an empty sigData) and
     *                  sig over that hash (uint) from the aggregate key
     * @param keyManager New KeyManager's address
     */
    function updateKeyManager(SigData calldata sigData, IKeyManager keyManager)
        external
        nzAddr(address(keyManager))
        updatedValidSig(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.updateKeyManager.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    keyManager
                )
            )
        )
    {
        _keyManager = keyManager;
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
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external view override returns (IKeyManager) {
        return _keyManager;
    }

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

    /// @dev    Call isUpdatedValidSig in _keyManager
    modifier updatedValidSig(SigData calldata sigData, bytes32 contractMsgHash) {
        // Disable check for reason-string because it should not trigger. The function
        // inside should either revert or return true, never false. Require just seems healthy
        // solhint-disable-next-line reason-string
        require(_keyManager.isUpdatedValidSig(sigData, contractMsgHash));
        _;
    }

    /// @notice Ensure that the caller is the KeyManager's governor address.
    modifier isGovernor() {
        require(msg.sender == _keyManager.getGovernanceKey(), "Staking: not governor");
        _;
    }
}
