pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./interfaces/IFLIP.sol";
import "./abstract/Shared.sol";

/**
 * @title    FLIP contract
 * @notice   The FLIP utility token which is used to stake in the FLIP system and pay for
 *           trap fees with
 * @author   Quantaf1re (James Key)
 */
contract FLIP is ERC20, ERC20Burnable, Ownable, Shared {
    constructor(
        string memory name,
        string memory symbol,
        address receiver,
        uint256 mintAmount
    ) ERC20(name, symbol) Ownable() nzAddr(receiver) nzUint(mintAmount) {
        _mint(receiver, mintAmount);
    }

    function mint(address receiver, uint256 amount) external nzAddr(receiver) nzUint(amount) onlyOwner {
        _mint(receiver, amount);
    }
}
