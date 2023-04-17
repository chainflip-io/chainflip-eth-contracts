pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./interfaces/IFLIP.sol";
import "./interfaces/IKeyManager.sol";
import "./abstract/Shared.sol";
import "./AggKeyNonceConsumer.sol";

/**
 * @title    FLIP contract
 * @notice   The FLIP utility token which is used to stake in the FLIP system and pay for
 *           trap fees with
 */
contract FLIP is ERC20, IFLIP, Shared {
    address public _stakeManager;

    // StakeManager and GenesisValidatorFlip are the same (stakeManager). We
    // leave them separate in case we consider having receiverGenesisValidatorFlip
    // be a different address for some reason. TBD.
    constructor(
        uint256 flipTotalSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake,
        address receiverGenesisValidatorFlip, // Stake Manager
        address receiverGenesisFlip,
        address stakeManager // Stake Manager
    )
        ERC20("Chainflip", "FLIP")
        nzAddr(receiverGenesisValidatorFlip)
        nzAddr(receiverGenesisFlip)
        nzUint(flipTotalSupply)
    {
        uint256 genesisValidatorFlip = numGenesisValidators * genesisStake;
        _mint(receiverGenesisValidatorFlip, genesisValidatorFlip);
        _mint(receiverGenesisFlip, flipTotalSupply - genesisValidatorFlip);
        _stakeManager = stakeManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    // Only the stateChain can mint/burn tokens via aggKey signed messages through the StakeManager.updateFlipSupply()
    // _mint already checks for address zero - TO TEST
    function mint(address receiver, uint amount) external override nzUint(amount) onlyStakeManager {
        _mint(receiver, amount);
    }

    // _burn already checks for address zero
    function burn(address stakeManager, uint amount) external override nzUint(amount) onlyStakeManager {
        _burn(stakeManager, amount);
    }

    function updateStakeManager(address newstakeManager) external override nzAddr(newstakeManager) onlyStakeManager {
        _stakeManager = newstakeManager;
    }

    modifier onlyStakeManager() {
        require(msg.sender == _stakeManager, "FLIP: only stakeManager");
        _;
    }
}
