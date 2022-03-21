pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./interfaces/IFLIP.sol";
import "./abstract/Shared.sol";
import "./interfaces/IKeyManager.sol";
import "./interfaces/IStakeManager.sol";

/**
 * @title    FLIP contract
 * @notice   The FLIP utility token which is used to stake in the FLIP system and pay for
 *           trap fees with
 * @author   Quantaf1re (James Key)
 */
contract FLIP is ERC20, Ownable, Shared {
    event FlipSupplyUpdated(uint256 oldSupply, uint256 newSupply, uint256 stateChainBlockNumber);

    IKeyManager private _keyManager;

    /// @dev    The last time that the State Chain updated the totalSupply
    uint256 private _lastSupplyUpdateBlockNum = 0;

    constructor(
        string memory name,
        string memory symbol,
        uint256 flipTotalSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake,
        address receiverGenesisValidatorFlip, // Stake Manager
        IKeyManager keyManager
    ) ERC20(name, symbol) Ownable() nzAddr(receiverGenesisValidatorFlip) nzUint(flipTotalSupply) {
        uint256 genesisValidatorFlip = numGenesisValidators * genesisStake;
        _mint(receiverGenesisValidatorFlip, genesisValidatorFlip);
        _mint(msg.sender, flipTotalSupply - genesisValidatorFlip);

        // PROBLEM: StakeManager requires FLIP on constructor and FLIP requires reciever (StakeManager) on constructor
        _keyManager = keyManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Compares a given new FLIP supply against the old supply,
     *          then mints and burns as appropriate
     * @param sigData               signature over the abi-encoded function params
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     * @param staker Staking contract owner of the tokens to be minted/burnt
     */
    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber,
        address staker
    )
        external
        nzUint(newTotalSupply)
        updatedValidSig(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.updateFlipSupply.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    newTotalSupply,
                    stateChainBlockNumber,
                    staker
                )
            )
        )
    {
        require(stateChainBlockNumber > _lastSupplyUpdateBlockNum, "Staking: old FLIP supply update");
        _lastSupplyUpdateBlockNum = stateChainBlockNumber;
        uint256 oldSupply = totalSupply();
        if (newTotalSupply < oldSupply) {
            uint256 amount = oldSupply - newTotalSupply;
            _burn(staker, amount);
        } else if (newTotalSupply > oldSupply) {
            uint256 amount = newTotalSupply - oldSupply;
            _mint(staker, amount);
        }
        emit FlipSupplyUpdated(oldSupply, newTotalSupply, stateChainBlockNumber);
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

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the last state chain block number of the last supply update
     * @return  The state chain block number of the last supply update
     */
    function getLastSupplyUpdateBlockNumber() external view returns (uint256) {
        return _lastSupplyUpdateBlockNum;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Call isUpdatedValidSig in _keyManager
    modifier updatedValidSig(SigData calldata sigData, bytes32 contractMsgHash) {
        require(_keyManager.isUpdatedValidSig(sigData, contractMsgHash));
        _;
    }
}
