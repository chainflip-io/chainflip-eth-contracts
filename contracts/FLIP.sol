pragma solidity ^0.8.0;


import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./abstract/Shared.sol";


/**
* @title    FLIP contract
* @notice   The FLIP utility token which is used to stake in the FLIP system and pay for
*           trap fees with
* @author   Quantaf1re (James Key)
*/
contract FLIP is ERC20, Ownable, Shared {
    
    constructor(
        string memory name, 
        string memory symbol, 
        address receiver, 
        uint256 mintAmount
    ) ERC20(name, symbol) Ownable() {
        _mint(receiver, mintAmount);
    }

    function mint(address receiver, uint amount) external nzAddr(receiver) nzUint(amount) onlyOwner {
        _mint(receiver, amount);
    }
}
