pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/IStateChainGateway.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IFlipIssuer.sol";
import "./interfaces/IFLIP.sol";
import "./AggKeyNonceConsumer.sol";
import "./GovernanceCommunityGuarded.sol";

/**
 * @title    State Chain Gateway contract
 * @notice   Manages the funding and redemption FLIP from/to stateChain accounts.
 *           Accounts on the FLIP state chain basically have full control
 *           of FLIP leaving the contract. FLIP can be added to the StateChain
 *           account via `fundStateChainAccount` with their stateChain nodeID.
 *
 *           This contract also handles the minting and burning of FLIP after the
 *           initial supply is minted during FLIP's creation. At any time, a
 *           valid aggragate signature can be submitted to the contract which
 *           updates the total supply by minting or burning the necessary FLIP.
 */
contract StateChainGateway is IFlipIssuer, IStateChainGateway, AggKeyNonceConsumer, GovernanceCommunityGuarded {
    /// @dev    The FLIP token address. To be set only once after deployment via setFlip.
    // solhint-disable-next-line var-name-mixedcase
    IFLIP private _FLIP;

    /// @dev    The minimum amount of FLIP needed to fund an account, to prevent spamming
    uint256 private _minFunding;
    /// @dev    Holding pending redemptions for the 48h withdrawal delay
    mapping(bytes32 => Redemption) private _pendingRedemptions;
    /// @dev   Time after registerRedemption required to wait before call to executeRedemption
    uint48 public constant REDEMPTION_DELAY = 2 days;

    /// @dev    The last block number in which the State Chain updated the totalSupply
    uint256 private _lastSupplyUpdateBlockNum = 0;

    // Defined in IStateChainGateway, just here for convenience
    // struct Redemption {
    //     uint amount;
    //     address funder;
    //     // 48 so that 160 (from funder) + 48 + 48 is 256 they can all be packed
    //     // into a single 256 bit slot
    //     uint48 startTime;
    //     uint48 expiryTime;
    // }

    constructor(IKeyManager keyManager, uint256 minFunding) AggKeyNonceConsumer(keyManager) {
        _minFunding = minFunding;
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

    /**
     * @notice  Get the FLIP token address
     * @dev     This function and it's return value will be checked when updating the FLIP issuer.
     *          Do not remove nor modify this function in future versions of this contract.
     * @return  The address of FLIP
     */
    function getFLIP() external view override returns (IFLIP) {
        return _FLIP;
    }

    /// @dev   Ensure that a new keyManager has the getGovernanceKey() and getCommunityKey()
    ///        functions implemented. These are functions required for this contract to
    ///        to at least be able to use the emergency mechanism.
    function _checkUpdateKeyManager(IKeyManager keyManager, bool omitChecks) internal view override {
        address newGovKey = keyManager.getGovernanceKey();
        address newCommKey = keyManager.getCommunityKey();

        if (!omitChecks) {
            // Ensure that the keys are the same
            require(newGovKey == _getGovernor() && newCommKey == _getCommunityKey());

            Key memory newAggKey = keyManager.getAggregateKey();
            Key memory currentAggKey = getKeyManager().getAggregateKey();

            require(
                newAggKey.pubKeyX == currentAggKey.pubKeyX && newAggKey.pubKeyYParity == currentAggKey.pubKeyYParity
            );
        } else {
            // Check that the addresses have been initialized
            require(newGovKey != address(0) && newCommKey != address(0));
        }
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
     *          should be called. Deployed via DeployerContract.sol so it can't be frontrun.
     *          The FLIP address can only be set once.
     * @param flip FLIP token address
     */
    function setFlip(IFLIP flip) external override nzAddr(address(flip)) {
        require(address(_FLIP) == address(0), "Gateway: Flip address already set");
        _FLIP = flip;
        emit FLIPSet(address(flip));
    }

    /**
     * @notice          Add FLIP funds to a StateChain account identified with a nodeID
     * @dev             Requires the funder to have called `approve` in FLIP
     * @param amount    The amount of FLIP tokens
     * @param nodeID    The nodeID of the funder
     */
    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external override nzBytes32(nodeID) {
        IFLIP flip = _FLIP;
        require(address(flip) != address(0), "Gateway: Flip not set");
        require(amount >= _minFunding, "Gateway: not enough funds");
        // Assumption of set token allowance by the user
        flip.transferFrom(msg.sender, address(this), amount);
        emit Funded(nodeID, amount, msg.sender);
    }

    /**
     * @notice  Redeem FLIP from the StateChain. The State Chain will determine the amount
     *          that can be redeemed, but a basic calculation for a validator would be:
     *          amount redeemable = stake + rewards - penalties.
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param nodeID    The nodeID of the funder
     * @param amount    The amount of funds to be locked up
     * @param funder    The funder who is sending the FLIP
     * @param expiryTime   The last valid timestamp that can execute this redemption (uint48)
     */
    function registerRedemption(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address funder,
        uint48 expiryTime
    )
        external
        override
        onlyNotSuspended
        nzBytes32(nodeID)
        nzUint(amount)
        nzAddr(funder)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.registerRedemption.selector, nodeID, amount, funder, expiryTime))
        )
    {
        require(
            // Must be fresh or have been executed & deleted, or past the expiry
            block.timestamp > uint256(_pendingRedemptions[nodeID].expiryTime),
            "Gateway: a pending redemption exists"
        );

        uint48 startTime = uint48(block.timestamp) + REDEMPTION_DELAY;
        require(expiryTime > startTime, "Gateway: expiry time too soon");

        _pendingRedemptions[nodeID] = Redemption(amount, funder, startTime, expiryTime);
        emit RedemptionRegistered(nodeID, amount, funder, startTime, expiryTime);
    }

    /**
     * @notice  Execute a pending redemption to get back funds. Cannot execute a pending
     *          redemption before 48h have passed after registering it, or after the specified
     *          expiry time
     * @dev     No need for nzUint(nodeID) since that is handled by `redemption.expiryTime > 0`
     * @param nodeID    The nodeID of the funder
     */
    function executeRedemption(bytes32 nodeID) external override onlyNotSuspended {
        Redemption memory redemption = _pendingRedemptions[nodeID];
        require(
            block.timestamp >= redemption.startTime && redemption.expiryTime > 0,
            "Gateway: early or already execd"
        );

        // Housekeeping
        delete _pendingRedemptions[nodeID];

        if (block.timestamp <= redemption.expiryTime) {
            emit RedemptionExecuted(nodeID, redemption.amount);

            // Send the tokens
            _FLIP.transfer(redemption.funder, redemption.amount);
        } else {
            emit RedemptionExpired(nodeID, redemption.amount);
        }
    }

    /**
     * @notice  Compares a given new FLIP supply against the old supply and mints or burns
     *          FLIP tokens from this contract as appropriate.
     *          It requires a message signed by the aggregate key.
     * @dev     Hardcoded to only mint and burn FLIP tokens to/from this contract.
     * @param sigData               Struct containing the signature data over the message
     *                              to verify, signed by the aggregate key.
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     */
    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber
    )
        external
        override
        onlyNotSuspended
        nzUint(newTotalSupply)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.updateFlipSupply.selector, newTotalSupply, stateChainBlockNumber))
        )
    {
        require(stateChainBlockNumber > _lastSupplyUpdateBlockNum, "Gateway: old FLIP supply update");
        _lastSupplyUpdateBlockNum = stateChainBlockNumber;
        IFLIP flip = _FLIP;
        uint256 oldSupply = flip.totalSupply();
        if (newTotalSupply < oldSupply) {
            uint256 amount = oldSupply - newTotalSupply;
            flip.burn(address(this), amount);
        } else if (newTotalSupply > oldSupply) {
            uint256 amount = newTotalSupply - oldSupply;
            flip.mint(address(this), amount);
        }
        emit FlipSupplyUpdated(oldSupply, newTotalSupply, stateChainBlockNumber);
    }

    /**
     * @notice  Updates the address that is allowed to issue FLIP tokens. This will be used when this
     *          contract needs an upgrade. A new contract will be deployed and all the FLIP will be
     *          transferred to it via the redemption process. Finally the right to issue FLIP will be transferred.
     * @dev     The new issuer must be a contract and, in a standard upgrade, it must have the reference FLIP address.
     *          In a special case where the check is omitted, the new issuer must be a contract, never an EOA.
     * @param sigData     Struct containing the signature data over the message
     *                    to verify, signed by the aggregate key.
     * @param newIssuer   New contract that will issue FLIP tokens.
     * @param omitChecks Allow the omission of the extra checks in a special case
     */
    function updateFlipIssuer(
        SigData calldata sigData,
        address newIssuer,
        bool omitChecks
    )
        external
        override
        onlyNotSuspended
        nzAddr(newIssuer)
        consumesKeyNonce(sigData, keccak256(abi.encode(this.updateFlipIssuer.selector, newIssuer, omitChecks)))
    {
        if (!omitChecks) {
            require(IFlipIssuer(newIssuer).getFLIP() == _FLIP, "Gateway: wrong FLIP ref");
        } else {
            require(newIssuer.code.length > 0);
        }

        _FLIP.updateIssuer(newIssuer);
    }

    /**
     * @notice      Set the minimum amount of funds needed for `fundStateChainAccount` to be able
     *              to be called. Used to prevent spamming of funding.
     * @param newMinFunding   The new minimum funding amount
     */
    function setMinFunding(uint256 newMinFunding) external override nzUint(newMinFunding) onlyGovernor {
        emit MinFundingChanged(_minFunding, newMinFunding);
        _minFunding = newMinFunding;
    }

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
    function getMinimumFunding() external view override returns (uint256) {
        return _minFunding;
    }

    /**
     * @notice  Get the pending redemption for the input nodeID. If there was never
     *          a pending redemption for this nodeID, or it has already been executed
     *          (and therefore deleted), it'll return (0, 0x00..., 0, 0)
     * @param nodeID   The nodeID which has a pending redemption
     * @return         The redemption (Redemption struct)
     */
    function getPendingRedemption(bytes32 nodeID) external view override returns (Redemption memory) {
        return _pendingRedemptions[nodeID];
    }

    /**
     * @notice  Get the last state chain block number of the last supply update
     * @return  The state chain block number of the last supply update
     */
    function getLastSupplyUpdateBlockNumber() external view override returns (uint256) {
        return _lastSupplyUpdateBlockNum;
    }
}
