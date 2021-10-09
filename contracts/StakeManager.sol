pragma solidity ^0.8.7;


import "./interfaces/IStakeManager.sol";
import "./interfaces/IKeyManager.sol";
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
contract StakeManager is Shared, IStakeManager, IERC777Recipient, ReentrancyGuard {

    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;
    /// @dev    The FLIP token
    FLIP private _FLIP;
    /// @dev    The last time that the State Chain updated the totalSupply
    uint private _lastSupplyUpdateBlockNum = 0; // initialise to never updated

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
    mapping(bytes32 => Claim) private _pendingClaims;
    // The number of seconds in 48h
    uint48 constant public CLAIM_DELAY = 2 days;

    IERC1820Registry constant private _ERC1820_REGISTRY = IERC1820Registry(0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24);
    address[] private _defaultOperators;
    bytes32 constant private TOKENS_RECIPIENT_INTERFACE_HASH = keccak256('ERC777TokensRecipient');


    // Defined in IStakeManager, just here for convenience
    // struct Claim {
    //     uint amount;
    //     address staker;
    //     // 48 so that 160 (from staker) + 48 + 48 is 256 they can all be packed
    //     // into a single 256 bit slot
    //     uint48 startTime;
    //     uint48 expiryTime;
    // }


    event Staked(bytes32 indexed nodeID, uint amount, address staker, address returnAddr);
    event ClaimRegistered(
        bytes32 indexed nodeID,
        uint amount,
        address staker,
        uint48 startTime,
        uint48 expiryTime
    );
    event ClaimExecuted(bytes32 indexed nodeID, uint amount);
    event FlipSupplyUpdated(uint oldSupply, uint newSupply, uint stateChainBlockNumber);
    event MinStakeChanged(uint oldMinStake, uint newMinStake);


    constructor(IKeyManager keyManager, uint minStake, uint flipTotalSupply, uint numGenesisValidators, uint genesisStake) {
        _keyManager = keyManager;
        _minStake = minStake;
        _defaultOperators.push(address(this));
        uint genesisValidatorFlip = numGenesisValidators * genesisStake;
        _totalStake = genesisValidatorFlip;
        _FLIP = new FLIP("ChainFlip", "FLIP", _defaultOperators, address(this), flipTotalSupply);
        _FLIP.transfer(msg.sender, flipTotalSupply - genesisValidatorFlip);
        _ERC1820_REGISTRY.setInterfaceImplementer(address(this), TOKENS_RECIPIENT_INTERFACE_HASH, address(this));
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
        uint amount,
        address returnAddr
    ) external override nonReentrant nzBytes32(nodeID) nzAddr(returnAddr) noFish {
        require(amount >= _minStake, "StakeMan: stake too small");

        // Ensure FLIP is transferred and update _totalStake. Technically this `require` shouldn't
        // be necessary, but since this is mission critical, it's worth being paranoid
        uint balBefore = _FLIP.balanceOf(address(this));
        _FLIP.operatorSend(msg.sender, address(this), amount, "", "stake");
        require(_FLIP.balanceOf(address(this)) == balBefore + amount, "StakeMan: token transfer failed");

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
        uint amount,
        address staker,
        uint48 expiryTime
    ) external override nonReentrant nzBytes32(nodeID) nzUint(amount) nzAddr(staker) noFish updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.registerClaim.selector,
                SigData(0, 0, sigData.nonce, address(0)),
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
    function executeClaim(bytes32 nodeID) external override noFish {
        Claim memory claim = _pendingClaims[nodeID];
        require(
            uint(block.timestamp) >= claim.startTime &&
            uint(block.timestamp) <= claim.expiryTime,
            "StakeMan: early, late, or execd"
        );

        // Housekeeping
        delete _pendingClaims[nodeID];
        _totalStake -= claim.amount;
        emit ClaimExecuted(nodeID, claim.amount);

        // Send the tokens
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
        uint newTotalSupply,
        uint stateChainBlockNumber
    ) external override nzUint(newTotalSupply) noFish refundGas updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.updateFlipSupply.selector,
                SigData(0, 0, sigData.nonce, address(0)),
                newTotalSupply,
                stateChainBlockNumber
            )
        ),
        KeyID.Agg
    ) {
        require(stateChainBlockNumber > _lastSupplyUpdateBlockNum, "StakeMan: old FLIP supply update");
        _lastSupplyUpdateBlockNum = stateChainBlockNumber;
        FLIP flip = _FLIP;
        uint oldSupply = flip.totalSupply();
        if (newTotalSupply < oldSupply) {
            flip.burn(oldSupply - newTotalSupply, "");
        } else if (newTotalSupply > oldSupply) {
            flip.mint(address(this), newTotalSupply - oldSupply, "", "");
        }
        emit FlipSupplyUpdated(oldSupply, newTotalSupply, stateChainBlockNumber);
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
    ) external override nzUint(newMinStake) noFish updatedValidSig(
        sigData,
        keccak256(
            abi.encodeWithSelector(
                this.setMinStake.selector,
                SigData(0, 0, sigData.nonce, address(0)),
                newMinStake
            )
        ),
        KeyID.Gov
    ) {
        emit MinStakeChanged(_minStake, newMinStake);
        _minStake = newMinStake;
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

    /**
     *  @notice Allows this contract to receive ETH used to refund callers
     */
    receive () external payable {}


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external override view returns (IKeyManager) {
        return _keyManager;
    }

    /**
     * @notice  Get the FLIP token address
     * @return  The address of FLIP
     */
    function getFLIPAddress() external override view returns (address) {
        return address(_FLIP);
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
    function getMinimumStake() external override view returns (uint) {
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


    /// @dev    Call isValidSig in _keyManager
    modifier updatedValidSig(
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
