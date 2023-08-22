// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./IFLIP.sol";
import "./IAggKeyNonceConsumer.sol";
import "./IGovernanceCommunityGuarded.sol";
import "./IFlipIssuer.sol";

/**
 * @title    StateChainGateway interface
 */
interface IStateChainGateway is IGovernanceCommunityGuarded, IFlipIssuer, IAggKeyNonceConsumer {
    event Funded(bytes32 indexed nodeID, uint256 amount, address funder);
    event RedemptionRegistered(
        bytes32 indexed nodeID,
        uint256 amount,
        address indexed redeemAddress,
        uint48 startTime,
        uint48 expiryTime,
        address executor
    );
    event RedemptionExecuted(bytes32 indexed nodeID, uint256 amount);
    event RedemptionExpired(bytes32 indexed nodeID, uint256 amount);
    event MinFundingChanged(uint256 oldMinFunding, uint256 newMinFunding);
    event GovernanceWithdrawal(address to, uint256 amount);
    event FLIPSet(address flip);
    event FlipSupplyUpdated(uint256 oldSupply, uint256 newSupply, uint256 stateChainBlockNumber);

    struct Redemption {
        uint256 amount;
        address redeemAddress;
        // 48 so that 160 (from redeemAddress) + 48 + 48 is 256 they can all be packed
        // into a single 256 bit slot
        uint48 startTime;
        uint48 expiryTime;
        address executor;
    }

    /**
     * @notice  Sets the FLIP address after initialization. We can't do this in the constructor
     *          because FLIP contract requires this contract's address on deployment for minting.
     *          First this contract is deployed, then the FLIP contract and finally setFLIP
     *          should be called. OnlyDeployer modifer for added security since tokens will be
     *          minted to this contract before calling setFLIP.
     * @param flip FLIP token address
     */
    function setFlip(IFLIP flip) external;

    /**
     * @notice          Add FLIP funds to a StateChain account identified with a nodeID
     * @dev             Requires the funder to have called `approve` in FLIP
     * @param amount    The amount of FLIP tokens
     * @param nodeID    The nodeID of the account to fund
     */
    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external;

    /**
     * @notice  Redeem FLIP from the StateChain. The State Chain will determine the amount
     *          that can be redeemed, but a basic calculation for a validator would be:
     *          amount redeemable = stake + rewards - penalties.
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param nodeID    The nodeID of the account redeeming the FLIP
     * @param amount    The amount of funds to be locked up
     * @param redeemAddress    The redeemAddress who will receive the FLIP
     * @param expiryTime   The last valid timestamp that can execute this redemption (uint48)
     */
    function registerRedemption(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address redeemAddress,
        uint48 expiryTime,
        address executor
    ) external;

    /**
     * @notice  Execute a pending redemption to get back funds. Cannot execute a pending
     *          redemption before 48h have passed after registering it, or after the specified
     *          expiry time
     * @dev     No need for nzUint(nodeID) since that is handled by `redemption.expiryTime > 0`
     * @param nodeID    The nodeID of the account redeeming the FLIP
     * @return          The address that received the FLIP and the amount
     */
    function executeRedemption(bytes32 nodeID) external returns (address, uint256);

    /**
     * @notice  Compares a given new FLIP supply against the old supply and mints or burns
     *          FLIP tokens from this contract as appropriate.
     *          It requires a message signed by the aggregate key.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     */
    function updateFlipSupply(SigData calldata sigData, uint256 newTotalSupply, uint256 stateChainBlockNumber) external;

    /**
     * @notice  Updates the address that is allowed to issue FLIP tokens. This will be used when this
     *          contract needs an upgrade. A new contract will be deployed and all the FLIP will be
     *          transferred to it via the redemption process. Finally the right to issue FLIP will be transferred.
     * @param sigData     Struct containing the signature data over the message
     *                    to verify, signed by the aggregate key.
     * @param newIssuer   New contract that will issue FLIP tokens.
     * @param omitChecks Allow the omission of the extra checks in a special case
     */
    function updateFlipIssuer(SigData calldata sigData, address newIssuer, bool omitChecks) external;

    /**
     * @notice      Set the minimum amount of funds needed for `fundStateChainAccount` to be able
     *              to be called. Used to prevent spamming of funding.
     * @param newMinFunding   The new minimum funding amount
     */
    function setMinFunding(uint256 newMinFunding) external;

    /**
     * @notice Withdraw all FLIP to governance address in case of emergency. This withdrawal needs
     *         to be approved by the Community, it is a last resort. Used to rectify an emergency.
     *         The governance address is also updated as the issuer of FLIP.
     */
    function govWithdraw() external;

    /**
     * @notice Update the FLIP Issuer address with the governance address in case of emergency.
     *         This needs to be approved by the Community, it is a last resort. Used to rectify
     *         an emergency.
     */
    function govUpdateFlipIssuer() external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the minimum amount of funds that's required for funding
     *          an account on the StateChain.
     * @return  The minimum amount (uint)
     */
    function getMinimumFunding() external view returns (uint256);

    /**
     * @notice  Get the pending redemption for the input nodeID. If there was never
     *          a pending redemption for this nodeID, or it has already been executed
     *          (and therefore deleted), it'll return (0, 0x00..., 0, 0)
     * @param nodeID   The nodeID which has a pending redemption
     * @return         The redemption (Redemption struct)
     */
    function getPendingRedemption(bytes32 nodeID) external view returns (Redemption memory);

    /**
     * @notice  Get the last state chain block number that the supply was updated at
     * @return  The state chain block number of the last update
     */
    function getLastSupplyUpdateBlockNumber() external view returns (uint256);
}
