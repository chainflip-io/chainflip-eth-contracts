pragma solidity ^0.8.0;


import "./interfaces/IKeyManager.sol";
import "./abstract/Shared.sol";
import "./FLIP.sol";
import "@openzeppelin/contracts/token/ERC777/IERC777Recipient.sol";
import "@openzeppelin/contracts/utils/introspection/IERC1820Registry.sol";

/**
* @title    StakeManager contract
* @notice   Manages the staking of FLIP. Validators on the FLIP state chain
*           basically have full control of FLIP leaving the contract. Auction
*           logic for validator slots is not handled in this contract - bidders
*           just send their bid to this contract via `stake` with their FLIP state chain
*           nodeID, the ChainFlip Engine witnesses the bids, takes the top n bids,
*           assigns them to slots, then signs/calls `claim` to refund everyone else.
*
*           This contract also handles the minting of FLIP after the initial supply
*           is minted during FLIP's creation. Every new block after the contract is created is
*           able to mint `_emissionPerBlock` amount of FLIP. This is FLIP that's meant to 
*           be rewarded to validators for their service. If none of them end up being naughty
*           boys or girls, then their proportion of that newly minted reward will be rewarded
*           to them based on their proportion of the total stake when they `claim` - though the logic of
*           assigning rewards is handled by the ChainFlip Engine via aggKey and this contract just blindly
*           trusts its judgement. There is an intentional limit on the power to mint, which is
*           why there's an emission rate controlled within the contract, so that a compromised
*           aggKey can't mint infinite tokens - the most that can be minted is any outstanding
*           emission of FLIP and the most that can be stolen is the FLIP balance of this contract,
*           which is the total staked (or bidded during auctions) + total emitted from rewards.
*           However, a compromised govKey could change the emission rate and therefore mint
*           infinite tokens.
* @author   Quantaf1re (James Key)
*/
contract StakeManager is Shared, IERC777Recipient {

    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;
    /// @dev    The FLIP token
    FLIP private _FLIP;
    /// @dev    The last time that claim was called, so we know how much to mint now
    uint private _lastMintBlockNum;
    /// @dev    The amount of FLIPs emitted per second, minted when `claim` is called
    uint private _emissionPerBlock;
    /**
     * @dev     This tracks the amount of FLIP that should be in this contract currently. It's
     *          equal to the total staked - total claimed + total minted (above initial
     *          supply). If there's some bug that drains FLIP from this contract that
     *          isn't part of `claim`, then `noFish` should protect against it. Note that
     *          if someone is slashed, _totalStake will not be reduced.
     */
    uint private _totalStake;
    /// @dev    The minimum amount of FLIP needed to stake, to prevent spamming
    uint private _minStake;
    /// @dev    Holding pending claims for the 48h withdrawal delay
    mapping(uint => Claim) private _pendingClaims;
    // The number of seconds in 48h
    uint48 constant public CLAIM_DELAY = 2 days;

    IERC1820Registry constant private _ERC1820_REGISTRY = IERC1820Registry(0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24);
    address[] private _defaultOperators;
    bytes32 constant private TOKENS_RECIPIENT_INTERFACE_HASH = keccak256('ERC777TokensRecipient');


    struct Claim {
        uint amount;
        address staker;
        // 48 so that 160 (from staker) + 48 + 48 is 256 they can all be packed
        // into a single 256 bit slot
        uint48 startTime;
        uint48 expiryTime;
    }


    event Staked(uint indexed nodeID, uint amount);
    event ClaimRegistered(
        uint indexed nodeID,
        uint amount,
        address staker,
        uint48 startTime,
        uint48 expiryTime
    );
    event ClaimExecuted(uint indexed nodeID, uint amount);
    event EmissionChanged(uint oldEmissionPerBlock, uint newEmissionPerBlock);
    event MinStakeChanged(uint oldMinStake, uint newMinStake);


    constructor(IKeyManager keyManager, uint emissionPerBlock, uint minStake, uint flipTotalSupply) {
        _keyManager = keyManager;
        _emissionPerBlock = emissionPerBlock;
        _minStake = minStake;
        _defaultOperators.push(address(this));
        _FLIP = new FLIP("ChainFlip", "FLIP", _defaultOperators, msg.sender, flipTotalSupply);
        _lastMintBlockNum = block.number;
        _ERC1820_REGISTRY.setInterfaceImplementer(address(this), TOKENS_RECIPIENT_INTERFACE_HASH, address(this));
    }


    function tokensReceived(
        address _operator,
        address _from,
        address _to,
        uint256 _amount,
        bytes calldata _data,
        bytes calldata _operatorData
    ) external override {
        require(msg.sender == address(_FLIP), "StakeMan: non-FLIP token");
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
     */
    function stake(uint nodeID, uint amount) external nzUint(nodeID) noFish {
        require(amount >= _minStake, "StakeMan: stake too small");

        // Ensure FLIP is transferred and update _totalStake. Technically this `require` shouldn't
        // be necessary, but since this is mission critical, it's worth being paranoid
        uint balBefore = _FLIP.balanceOf(address(this));
        _FLIP.operatorSend(msg.sender, address(this), amount, "", "");
        require(_FLIP.balanceOf(address(this)) == balBefore + amount, "StakeMan: token transfer failed");

        _totalStake += amount;
        emit Staked(nodeID, amount);
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
        uint nodeID,
        uint amount,
        address staker,
        uint48 expiryTime
    ) external nzUint(nodeID) nzUint(amount) nzAddr(staker) noFish validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.registerClaim.selector,
                SigData(0, 0),
                nodeID,
                amount,
                staker,
                expiryTime
            )
        ),
        KeyID.Agg
    ) {
        require(
            // Must be fresh or have been executed & deleted, or past the expiry
            block.timestamp > uint(_pendingClaims[nodeID].expiryTime),
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
     *          expiry block height
     * @dev     No need for nzUint(nodeID) since that is handled by
     *          `uint(block.number) <= claim.startTime`
     * @param nodeID    The nodeID of the staker
     */
    function executeClaim(
        uint nodeID
    ) external noFish {
        Claim memory claim = _pendingClaims[nodeID];
        require(
            uint(block.timestamp) >= claim.startTime &&
            uint(block.timestamp) <= claim.expiryTime,
            "StakeMan: early, late, or execd"
        );

        // If time has elapsed since the last mint, printer go brrrr
        _mintInflation();

        // Send the tokens and update _totalStake
        require(_FLIP.transfer(claim.staker, claim.amount));
        _totalStake -= claim.amount;

        // Housekeeping
        delete _pendingClaims[nodeID];
        emit ClaimExecuted(nodeID, claim.amount);
    }

    /**
     * @notice  Set the rate (per second) at which new FLIP is minted to this contract
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current governance key (uint)
     * @param newEmissionPerBlock     The new rate
     */
    function setEmissionPerBlock(
        SigData calldata sigData,
        uint newEmissionPerBlock
    ) external nzUint(newEmissionPerBlock) noFish validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.setEmissionPerBlock.selector,
                SigData(0, 0),
                newEmissionPerBlock
            )
        ),
        KeyID.Gov
    ) {
        // If time has elapsed since the last mint, printer go brrrr
        _mintInflation();

        emit EmissionChanged(_emissionPerBlock, newEmissionPerBlock);
        _emissionPerBlock = newEmissionPerBlock;
    }

    /**
     * @notice      Set the minimum amount of stake needed for `stake` to be able
     *              to be called. Used to prevent spamming of stakes.
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current governance key (uint)
     * @param newMinStake   The new minimum stake
     */
    function setMinStake(
        SigData calldata sigData,
        uint newMinStake
    ) external nzUint(newMinStake) noFish validSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.setMinStake.selector,
                SigData(0, 0),
                newMinStake
            )
        ),
        KeyID.Gov
    ) {
        emit MinStakeChanged(_minStake, newMinStake);
        _minStake = newMinStake;
    }

    /**
     * @notice  Mints any outstanding FLIP and updates _totalStake & _lastMintBlockNum
     *          if there was any to mint
     */
    function _mintInflation() private {
        if (block.number > _lastMintBlockNum) {
            uint amount = getInflationInFuture(0);
            _FLIP.mint(address(this), amount, "", "");
            _totalStake += amount;
            _lastMintBlockNum = block.number;
        }
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external view returns (IKeyManager) {
        return _keyManager;
    }

    /**
     * @notice  Get the FLIP token address
     * @return  The address of FLIP
     */
    function getFLIPAddress() external view returns (address) {
        return address(_FLIP);
    }

    /**
     * @notice  Get the last time that claim() was called, in unix time
     * @return  The time of the last claim (uint)
     */
    function getLastMintBlockNum() external view returns (uint) {
        return _lastMintBlockNum;
    }

    /**
     * @notice  Get the emission rate of FLIP in seconds
     * @return  The rate of FLIP emission (uint)
     */
    function getEmissionPerBlock() external view returns (uint) {
        return _emissionPerBlock;
    }

    /**
     * @notice  Get the amount of FLIP that would be emitted via inflation at
     *          the current block plus addition inflation from an extra
     *          `blocksIntoFuture` blocks
     * @param blocksIntoFuture  The number of blocks past the current block to
     *              calculate the inflation at
     * @return  The amount of FLIP inflation
     */
    function getInflationInFuture(uint blocksIntoFuture) public view returns (uint) {
        return (block.number + blocksIntoFuture - _lastMintBlockNum) * _emissionPerBlock;
    }

    /**
     * @notice  Get the total amount of FLIP currently staked by all stakers
     *          plus the inflation that could be minted if someone called
     *          `claim` or `setEmissionPerBlock` at the specified block
     * @param blocksIntoFuture  The number of blocks into the future added
     *              onto the current highest block. E.g. if the current highest
     *              block is 10, and the stake + inflation that you want to know
     *              is at height 15, input 5
     * @return  The total of stake + inflation at specified blocks in the future from now
     */
    function getTotalStakeInFuture(uint blocksIntoFuture) external view returns (uint) {
        // return _totalStake;
        return _totalStake + getInflationInFuture(blocksIntoFuture);
    }

    /**
     * @notice  Get the minimum amount of stake that's required for a bid
     *          attempt in the auction to be valid - used to prevent sybil attacks
     * @return  The minimum stake (uint)
     */
    function getMinimumStake() external view returns (uint) {
        return _minStake;
    }

    /**
     * @notice  Get the pending claim for the input nodeID. If there was never
     *          a pending claim for this nodeID, or it has already been executed
     *          (and therefore deleted), it'll return (0, 0x00..., 0, 0)
     * @return  The claim (Claim)
     */
    function getPendingClaim(uint nodeID) external view returns (Claim memory) {
        return _pendingClaims[nodeID];
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    
    /// @dev    Call isValidSig in _keyManager
    modifier validSig(
        SigData calldata sigData,
        bytes32 contractMsgHash,
        KeyID keyID
    ) {
        require(_keyManager.isValidSig(sigData, contractMsgHash, keyID));
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
