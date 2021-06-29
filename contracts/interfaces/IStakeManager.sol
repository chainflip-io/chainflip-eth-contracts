pragma solidity ^0.8.6;


import "./IKeyManager.sol";
import "./IShared.sol";


/**
* @title    StakeManager interface
* @author   Quantaf1re (James Key)
*/
interface IStakeManager is IShared {

    struct Claim {
        uint amount;
        address staker;
        // 48 so that 160 (from staker) + 48 + 48 is 256 they can all be packed
        // into a single 256 bit slot
        uint48 startTime;
        uint48 expiryTime;
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
        uint amount,
        address returnAddr
    ) external;

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
    ) external;

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
    function executeClaim(bytes32 nodeID) external;

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
    ) external;

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
    ) external;


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external view returns (IKeyManager);

    /**
     * @notice  Get the FLIP token address
     * @return  The address of FLIP
     */
    function getFLIPAddress() external view returns (address);

    /**
     * @notice  Get the last time that claim() was called, in unix time
     * @return  The time of the last claim (uint)
     */
    function getLastMintBlockNum() external view returns (uint);

    /**
     * @notice  Get the emission rate of FLIP in seconds
     * @return  The rate of FLIP emission (uint)
     */
    function getEmissionPerBlock() external view returns (uint);

    /**
     * @notice  Get the amount of FLIP that would be emitted via inflation at
     *          the current block plus addition inflation from an extra
     *          `blocksIntoFuture` blocks
     * @param blocksIntoFuture  The number of blocks past the current block to
     *              calculate the inflation at
     * @return  The amount of FLIP inflation
     */
    function getInflationInFuture(uint blocksIntoFuture) external view returns (uint);

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
    function getTotalStakeInFuture(uint blocksIntoFuture) external view returns (uint);

    /**
     * @notice  Get the minimum amount of stake that's required for a bid
     *          attempt in the auction to be valid - used to prevent sybil attacks
     * @return  The minimum stake (uint)
     */
    function getMinimumStake() external view returns (uint);

    /**
     * @notice  Get the pending claim for the input nodeID. If there was never
     *          a pending claim for this nodeID, or it has already been executed
     *          (and therefore deleted), it'll return (0, 0x00..., 0, 0)
     * @param nodeID    The nodeID which is has a pending claim
     * @return  The claim (Claim)
     */
    function getPendingClaim(bytes32 nodeID) external view returns (Claim memory);
}
