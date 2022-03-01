pragma solidity ^0.8.0;

import "./interfaces/IStakeManager.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IFLIP.sol";
import "./abstract/Shared.sol";
import "./FLIP.sol";
import "@openzeppelin/contracts/token/ERC777/IERC777Recipient.sol";
import "@openzeppelin/contracts/utils/introspection/IERC1820Registry.sol";
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
contract StakeManager is
    Shared,
    IStakeManager,
    IERC777Recipient,
    ReentrancyGuard
{
    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private immutable _keyManager;
    /// @dev    The FLIP token
    // solhint-disable-next-line var-name-mixedcase
    FLIP private immutable _FLIP;
    /// @dev    The last time that the State Chain updated the totalSupply
    uint256 private _lastSupplyUpdateBlockNum = 0; // initialise to never updated
    /// @dev    Whether execution of claims is suspended. Used in emergencies.
    bool public suspended = false;

    /**
     * @dev     This tracks the amount of FLIP that should be in this contract currently. It's
     *          equal to the total staked - total claimed + total minted (above initial
     *          supply). If there's some bug that drains FLIP from this contract that
     *          isn't part of `claim`, then `noFish` should protect against it. Note that
     *          if someone is slashed, _totalStake will not be reduced.
     */
    uint256 private _totalStake;
    /// @dev    The minimum amount of FLIP needed to stake, to prevent spamming
    uint256 private _minStake;
    /// @dev    Holding pending claims for the 48h withdrawal delay
    mapping(bytes32 => Claim) private _pendingClaims;
    /// @dev   Time after registerClaim required to wait before call to executeClaim
    uint48 public constant CLAIM_DELAY = 2 days;

    bytes32 private constant TOKENS_RECIPIENT_INTERFACE_HASH =
        keccak256("ERC777TokensRecipient");

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
        uint256 flipTotalSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake
    ) {
        _keyManager = keyManager;
        _minStake = minStake;

        address[] memory operators = new address[](1);
        operators[0] = address(this);
        uint256 genesisValidatorFlip = numGenesisValidators * genesisStake;
        _totalStake = genesisValidatorFlip;
        FLIP flip = new FLIP(
            "Chainflip",
            "FLIP",
            operators,
            address(this),
            flipTotalSupply
        );

        IERC1820Registry erc1820Reg = IERC1820Registry(
            0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24
        );
        erc1820Reg.setInterfaceImplementer(
            address(this),
            TOKENS_RECIPIENT_INTERFACE_HASH,
            address(this)
        );

        _FLIP = flip;
        flip.transfer(msg.sender, flipTotalSupply - genesisValidatorFlip);
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
    ) external override nonReentrant nzBytes32(nodeID) nzAddr(returnAddr) noFish {
        require(amount >= _minStake, "StakeMan: stake too small");

        // Store it in memory to save gas
        FLIP flip = _FLIP;

        // Ensure FLIP is transferred and update _totalStake. Technically this `require` shouldn't
        // be necessary, but since this is mission critical, it's worth being paranoid
        uint256 balBefore = flip.balanceOf(address(this));
        flip.operatorSend(msg.sender, address(this), amount, "", "stake");
        require(
            flip.balanceOf(address(this)) == balBefore + amount,
            "StakeMan: token transfer failed"
        );

        _totalStake += amount;
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
    ) external override nonReentrant nzBytes32(nodeID) nzUint(amount) nzAddr(staker) noFish updatedValidSig(
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
            "StakeMan: a pending claim exists"
        );

        uint48 startTime = uint48(block.timestamp) + CLAIM_DELAY;
        require(expiryTime > startTime, "StakeMan: expiry time too soon");

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
    function executeClaim(bytes32 nodeID) external override noFish {
        require(!suspended, "StakeMan: suspended");
        Claim memory claim = _pendingClaims[nodeID];
        require(
            uint256(block.timestamp) >= claim.startTime &&
                uint256(block.timestamp) <= claim.expiryTime,
            "StakeMan: early, late, or execd"
        );

        // Housekeeping
        delete _pendingClaims[nodeID];
        _totalStake -= claim.amount;
        emit ClaimExecuted(nodeID, claim.amount);

        // Send the tokens
        // solhint-disable-next-line reason-string
        require(_FLIP.transfer(claim.staker, claim.amount));
    }

    /**
     * @notice  Compares a given new FLIP supply against the old supply,
     *          then mints and burns as appropriate
     * @param sigData               signature over the abi-encoded function params
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     */
    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber
    ) external override nzUint(newTotalSupply) noFish updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.updateFlipSupply.selector,
                SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                newTotalSupply,
                stateChainBlockNumber
                )
            )
        )
    {
        require(
            stateChainBlockNumber > _lastSupplyUpdateBlockNum,
            "StakeMan: old FLIP supply update"
        );
        _lastSupplyUpdateBlockNum = stateChainBlockNumber;
        FLIP flip = _FLIP;
        uint256 oldSupply = flip.totalSupply();
        if (newTotalSupply < oldSupply) {
            uint256 amount = oldSupply - newTotalSupply;
            flip.burn(amount, "");
            _totalStake -= amount;
        } else if (newTotalSupply > oldSupply) {
            uint256 amount = newTotalSupply - oldSupply;
            flip.mint(address(this), amount, "", "");
            _totalStake += amount;
        }
        emit FlipSupplyUpdated(
            oldSupply,
            newTotalSupply,
            stateChainBlockNumber
        );
    }

    /**
     * @notice      Set the minimum amount of stake needed for `stake` to be able
     *              to be called. Used to prevent spamming of stakes.
     * @param newMinStake   The new minimum stake
     */
    function setMinStake(
        uint newMinStake
    ) external override nzUint(newMinStake) noFish isGovernor {
        emit MinStakeChanged(_minStake, newMinStake);
        _minStake = newMinStake;
    }

    /**
     * @notice      ERC1820 tokensReceived callback, doesn't do anything in our
     *              contract.
     * @param _operator         operator
     * @param _from             from
     * @param _to               to
     * @param _amount           amount
     * @param _data             data
     * @param _operatorData     operatorData
     */
    
    // solhint-disable no-unused-vars
    function tokensReceived(
        address _operator,
        address _from,
        address _to,
        uint256 _amount,
        bytes calldata _data,
        bytes calldata _operatorData
    ) external override {
        require(msg.sender == address(_FLIP), "StakeMan: non-FLIP token");
        require(_operator == address(this), "StakeMan: not the operator");
    }
    // solhint-enable no-unused-vars

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
        require(suspended, "StakeMan: Not suspended");
        address to = _keyManager.getGovernanceKey();
        uint256 amount = _FLIP.balanceOf(address(this));
        // solhint-disable-next-line reason-string
        require(_FLIP.transfer(to, amount));
        emit GovernanceWithdrawal(to, amount);
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
     * @notice  Get the last state chain block number of the last supply update
     * @return  The state chain block number of the last supply update
     */
    function getLastSupplyUpdateBlockNumber() external override view returns (uint) {
        return _lastSupplyUpdateBlockNum;
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
    function getPendingClaim(bytes32 nodeID) external override view returns (Claim memory) {
        return _pendingClaims[nodeID];
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////


    /// @dev    Call isUpdatedValidSig in _keyManager
    modifier updatedValidSig(
        SigData calldata sigData,
        bytes32 contractMsgHash
    ) {
        // solhint-disable-next-line reason-string
        require(_keyManager.isUpdatedValidSig(sigData, contractMsgHash));
        _;
    }

    /// @notice Ensure that the caller is the KeyManager's governor address.
    modifier isGovernor() {
        require(msg.sender == _keyManager.getGovernanceKey(), "StakeMan: not governor");
        _;
    }

    /// @notice Ensure that FLIP can only be withdrawn via `claim`
    ///         and not any other method
    modifier noFish() {
        _;
        // >= because someone could send some tokens to this contract and disable it if it was ==
        require(_FLIP.balanceOf(address(this)) >= _totalStake, "StakeMan: something smells fishy");
    }
}
