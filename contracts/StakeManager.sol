pragma solidity ^0.7.0;
pragma abicoder v2;


import "./interfaces/IKeyManager.sol";
import "./abstract/Shared.sol";
import "./FLIP.sol";


contract StakeManager is Shared {

    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;
    /// @dev    The FLIP token
    FLIP private _FLIP;
    /// @dev    The last time that claim was called, so we know how much to mint now
    uint private _lastMintBlockNum;
    /// @dev    The amount of FLIPs emitted per second, minted when `claim` is called
    uint private _emissionPerBlock;
    /// @dev    This tracks the amount of FLIP that should be in this contract currently. It's
    ///         equal to the total staked - total claimed + total minted (above initial
    ///         supply). If there's some bug that drains FLIP from this contract that
    ///         isn't part of `claim`, then `noFish` should protect against it
    uint private _totalStake;
    /// @dev    The minimum amount of FLIP needed to stake, to prevent spamming
    // Pulled this number out my ass
    uint private _minStake = (10**5) * _E_18;


    event Staked(uint indexed nodeID, uint amount);
    event Claimed(uint indexed nodeID, uint amount);
    event EmissionChanged(uint oldEmissionPerBlock, uint newEmissionPerBlock);
    event MinStakeChanged(uint oldMinStake, uint newMinStake);


    constructor(IKeyManager keyManager, uint emissionPerBlock, uint minStake, uint flipTotalSupply) {
        _keyManager = keyManager;
        _emissionPerBlock = emissionPerBlock;
        _minStake = minStake;
        _FLIP = new FLIP("ChainFlip", "FLIP", msg.sender, flipTotalSupply);
        _lastMintBlockNum = block.number;
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
        require(amount >= _minStake, "StakeMan: small stake, peasant");

        // Ensure FLIP is transferred and update _totalStake. Technically this `require` shouldn't
        // be necessary, but since this is mission critical, it's worth being paranoid
        uint balBefore = _FLIP.balanceOf(address(this));
        _FLIP.transferFrom(msg.sender, address(this), amount);
        require(_FLIP.balanceOf(address(this)) == balBefore + amount, "StakeMan: transfer failed");
        _totalStake += amount;

        emit Staked(nodeID, amount);
    }

    /**
     * @notice  Claim back stake. If only losing an auction, the same amount initially staked
     *          will be sent back. If losing an auction while being a validator,
                the amount sent back = stake + rewards - penalties, as determined by the CFE
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current aggregate key (uint)
     * @param nodeID    The nodeID of the staker
     * @param staker    The staker who is to be sent FLIP
     * @param amount    The amount of stake to be locked up
     */
    function claim(
        SigData calldata sigData,
        uint nodeID,
        address staker,
        uint amount
    ) external nzUint(nodeID) nzAddr(staker) nzUint(amount) noFish {
        require(
            _keyManager.isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.claim.selector,
                        SigData(0, 0),
                        nodeID,
                        staker,
                        amount
                    )
                ),
                sigData,
                KeyID.Agg
            )
        );

        // If time has elapsed since the last mint, printer go brrrr
        _mintInflation();

        // Send the tokens and update _totalStake
        _FLIP.transfer(staker, amount);
        _totalStake -= amount;

        emit Claimed(nodeID, amount);
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
    ) external nzUint(newEmissionPerBlock) noFish {
        require(
            _keyManager.isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.setEmissionPerBlock.selector,
                        SigData(0, 0),
                        newEmissionPerBlock
                    )
                ),
                sigData,
                KeyID.Gov
            )
        );
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
    ) external nzUint(newMinStake) noFish {
        require(
            _keyManager.isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.setMinStake.selector,
                        SigData(0, 0),
                        newMinStake
                    )
                ),
                sigData,
                KeyID.Gov
            )
        );

        emit MinStakeChanged(_minStake, newMinStake);
        _minStake = newMinStake;
    }

    // function mintInflation() external noFish {
    //     _mintInflation();
    // }

    function _mintInflation() private {
        if (block.number > _lastMintBlockNum) {
            uint amount = getInflationInFuture(0);
            _FLIP.mint(address(this), amount);
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


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @notice Ensure that FLIP can only be withdrawn via `claim`
    ///         and not any other method
    modifier noFish() {
        _;
        // >= because someone could send some tokens to this contract and disable it if it was ==
        require(_FLIP.balanceOf(address(this)) >= _totalStake, "StakeMan: something smells fishy");
    }
}
