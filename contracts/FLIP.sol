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
    address public _issuer;

    event IssuerUpdated(address oldIssuer, address newIssuer);

    // StakeManager and GenesisValidatorFlip are the same (stakeManager). We
    // leave them separate in case we consider having receiverGenesisValidatorFlip
    // be a different address for some reason. TBD.
    constructor(
        uint256 flipTotalSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake,
        address receiverGenesisValidatorFlip, // Stake Manager
        address receiverGenesisFlip,
        address issuer // Stake Manager
    )
        ERC20("Chainflip", "FLIP")
        nzAddr(receiverGenesisValidatorFlip)
        nzAddr(receiverGenesisFlip)
        nzUint(flipTotalSupply)
    {
        uint256 genesisValidatorFlip = numGenesisValidators * genesisStake;
        _mint(receiverGenesisValidatorFlip, genesisValidatorFlip);
        _mint(receiverGenesisFlip, flipTotalSupply - genesisValidatorFlip);
        _issuer = issuer;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    // TODO: What about calling this function increaseSupply and decreaseSupply?
    // TODO: We could to a two-step ownership transfer but given that this will be done through
    // the SC (not manually) and that we are always one bad tx away from disaster I'm not sure
    // this would add more than just complexity

    // Only the stateChain can mint/burn tokens via aggKey signed messages through the StakeManager.updateFlipSupply()
    // _mint already checks for address zero but not for zero amount
    // The StakeManager should not call this with amount = 0. But there is no real reason to revert.
    function mint(address account, uint amount) external override onlyIssuer {
        _mint(account, amount);
    }

    // _mint already checks for address zero but not for zero amount
    // The StakeManager should not call this with amount = 0. But there is no real reason to revert.
    function burn(address account, uint amount) external override onlyIssuer {
        _burn(account, amount);
    }

    function updateIssuer(address issuer) external override nzAddr(issuer) onlyIssuer {
        emit IssuerUpdated(_issuer, issuer);
        _issuer = issuer;
    }

    // TODO: Call it something bit more generic instead of StakeManager
    // Issuer, TokenIssuer, supplyManager, SupplyUpdater,TokenManager, TokenSupply...
    modifier onlyIssuer() {
        require(msg.sender == _issuer, "FLIP: only issuer");
        _;
    }
}
