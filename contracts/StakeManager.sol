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
    uint private _lastClaimTime;
    /// @dev    Equates to 15% per year (not compounding)
    uint private _emissionPerSec = 428082191780821917;
    /// @dev    Used to make make sure contract is collateralised at all times
    uint private _totalStaked;

    uint private constant _E_18 = 10**18;
    // Pulled this number out my ass
    uint private constant _MIN_STAKE = (10**5) * _E_18;


    event AuctionStarted(uint indexed auctionEndBlock);
    event Staked(uint indexed nodeID, uint amount);
    event Unstaked(uint indexed nodeID, uint amount);


    constructor(IKeyManager keyManager) {
        _keyManager = keyManager;
        _FLIP = new FLIP("ChainFlip", "FLIP", 9 * (10**7) * _E_18);
        _lastClaimTime = block.timestamp;
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
    function stake(uint amount, uint nodeID) external nzUint(amount) nzUint(nodeID) noFish {
        require(amount >= _MIN_STAKE, "StakeMan: small stake, peasant");

        // Ensure FLIP is transferred and update _totalStaked. Technically this `require` shouldn't
        // be necessary, but since this is mission critical, it's worth being paranoid
        uint balBefore = _FLIP.balanceOf(address(this));
        _FLIP.transferFrom(msg.sender, address(this), amount);
        require(_FLIP.balanceOf(address(this)) == balBefore + amount, "StakeMan: transfer failed");
        _totalStaked += amount;

        emit Staked(nodeID, amount);
    }

    /**
     * @notice  Claim back stake. If only losing an auction, the same amount initially staked
     *          will be sent back. If losing an auction while being a validator,
                the amount sent back = stake + rewards - penalties, as determined by the CFE
     * @param sigData   The keccak256 hash over the msg (uint) (which is the calldata
     *                  for this function with empty msgHash and sig) and sig over that hash
     *                  from the current governance key (uint)
     * @param staker    The staker who is to be sent FLIP
     * @param amount    The amount of stake to be locked up
     * @param nodeID    The nodeID of the staker
     */
    function claim(
        SigData calldata sigData,
        address staker,
        uint amount,
        uint nodeID
    ) external nzAddr(staker) nzUint(amount) nzUint(nodeID) noFish {
        require(
            _keyManager.isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.claim.selector,
                        SigData(0, 0),
                        staker,
                        nodeID,
                        amount
                    )
                ),
                sigData,
                _keyManager.getAggregateKey()
            )
        );

        // If time has elapsed since the last claim, printer go brrrr
        if (block.timestamp > _lastClaimTime) {
            _FLIP.mint(address(this), (block.timestamp - _lastClaimTime) * _emissionPerSec);
            _lastClaimTime = block.timestamp;
        }

        // Send the tokens and update _totalStaked
        _FLIP.transfer(staker, amount);
        _totalStaked -= amount;

        emit Unstaked(nodeID, amount);
    }

    function changeEmission(
        SigData calldata sigData,
        uint newEmissionPerSec
    ) external nzUint(newEmissionPerSec) {
        require(
            _keyManager.isValidSig(
                keccak256(
                    abi.encodeWithSelector(
                        this.changeEmission.selector,
                        SigData(0, 0),
                        newEmissionPerSec
                    )
                ),
                sigData,
                _keyManager.getGovernanceKey()
            )
        );

        _emissionPerSec = newEmissionPerSec;
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
    function getKeyManager() external returns (IKeyManager) {
        return _keyManager;
    }

    /**
     * @notice  Get the FLIP token address
     * @return  The address of FLIP
     */
    function getFLIPAddress() external returns (address) {
        return address(_FLIP);
    }

    /**
     * @notice  Get the last time that claim() was called, in unix time
     * @return  The time of the last claim (uint)
     */
    function getLastClaimTime() external returns (uint) {
        return _lastClaimTime;
    }

    /**
     * @notice  Get the emission rate of FLIP in seconds
     * @return  The rate of FLIP emission (uint)
     */
    function getEmissionPerSec() external returns (uint) {
        return _emissionPerSec;
    }

    /**
     * @notice  Get the total amount of FLIP currently staked by all stakers, used
     *          to always ensure collateralisation
     * @return  The current total of stake in this contract (uint)
     */
    function getTotalStaked() external returns (uint) {
        return _totalStaked;
    }

    /**
     * @notice  Get the minimum amount of stake that's required for a bid
     *          attempt in the auction to be valid - used to prevent sybil attacks
     * @return  The minimum stake (uint)
     */
    function getMinimumStake() external returns (uint) {
        return _MIN_STAKE;
    }


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @notice Ensure the contract is always collateralised
    modifier noFish() {
        require(_FLIP.balanceOf(address(this)) >= _totalStaked, "Stake: something smells fishy");
        _;
    }
}
