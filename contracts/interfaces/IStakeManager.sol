pragma solidity ^0.8.0;


import "./IKeyManager.sol";
import "./IFLIP.sol";
import "./IShared.sol";


/**
* @title    StakeManager interface
* @author   Quantaf1re (James Key)
*/
interface IStakeManager is IShared {
    
    event Staked(bytes32 indexed nodeID, uint amount, address staker, address indexed returnAddr);
    event ClaimRegistered(
        bytes32 indexed nodeID,
        uint amount,
        address indexed staker,
        uint48 startTime,
        uint48 expiryTime
    );
    event ClaimExecuted(bytes32 indexed nodeID, uint amount);
    event FlipSupplyUpdated(uint oldSupply, uint newSupply, uint stateChainBlockNumber);
    event MinStakeChanged(uint oldMinStake, uint newMinStake);

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
     * @notice  Compares a given new FLIP supply against the old supply,
     *          then mints new and burns as appropriate (to/from the StakeManager)
     * @param sigData               signature over the abi-encoded function params
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     */
    function updateFlipSupply(
        SigData calldata sigData,
        uint newTotalSupply,
        uint stateChainBlockNumber
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
    function getFLIP() external view returns (IFLIP);

    /**
     * @notice  Get the last state chain block number that the supply was updated at
     * @return  The state chain block number of the last update
     */
    function getLastSupplyUpdateBlockNumber() external view returns (uint);

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
