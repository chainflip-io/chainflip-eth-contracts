pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
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
contract FLIP is ERC20, ERC20Burnable, Ownable, Shared {


    IKeyManager private _keyManager;

    /// @dev    The last time that the State Chain updated the totalSupply
    uint256 private _lastSupplyUpdateBlockNum = 0;

    constructor(
        string memory name,
        string memory symbol,
        address receiver,
        uint256 mintAmount
    ) ERC20(name, symbol) Ownable() nzAddr(receiver) nzUint(mintAmount) {
        // To add initial minting logic or do it in another one-time callable function
        // to not require a reciever (aka StakeManager) when deploying it
        _mint(receiver, mintAmount);
        // Update Stake's manager _totalStake with the minted amount
    }

    function mint(address receiver, uint256 amount) external nzAddr(receiver) nzUint(amount) onlyOwner {
        _mint(receiver, amount);
    }

    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber,
        IStakeManager stakeManager
    )
        external
        nzUint(newTotalSupply)
        noFish(stakeManager) /** Slightly modifier version of the Stakemanager's noFish */ 
        updatedValidSig(
            sigData,
            keccak256(
                abi.encodeWithSelector(
                    this.updateFlipSupply.selector,
                    SigData(sigData.keyManAddr, sigData.chainID, 0, 0, sigData.nonce, address(0)),
                    newTotalSupply,
                    stateChainBlockNumber,
                    stakeManager
                )
            )
        )
    {
        // Burn and mint FLIP tokens
        // mint to the stakeManager provided
        // Store stateChainBlockNumber as _lastSupplyUpdateBlockNum
        // Update _totalStake stake on the StakeManager
        // stakeManager.updateTotalStake(bool, amount)
    }

    /**
     * @notice  Update KeyManager reference
                To be called right after deployment to set the key manager and when/if
                updating the keyManager contract.
     */
    function updateKeyManager(
        SigData calldata sigData,
        IKeyManager keyManager
    )
        external
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



    /// @dev    Call isUpdatedValidSig in _keyManager
    modifier updatedValidSig(SigData calldata sigData, bytes32 contractMsgHash) {
        // Disable check for reason-string because it should not trigger. The function
        // inside should either revert or return true, never false. Require just seems healthy
        // solhint-disable-next-line reason-string
        require(_keyManager.isUpdatedValidSig(sigData, contractMsgHash));
        _;
    }

    /// @notice Ensure that FLIP can only be withdrawn via `claim`
    ///         and not any other method
    ///         Adapted from StakeManagers
    modifier noFish(IStakeManager stakeManager) {
        _;
        // >= because someone could send some tokens to this contract and disable it if it was ==
        require(balanceOf(address(stakeManager)) >= stakeManager.getTotalStake(), "Staking: something smells fishy");
    }
}
