pragma solidity ^0.7.0;


import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";


contract FLIP is ERC20, Ownable {
    
    constructor (string memory name, string memory symbol, uint256 mintAmount) ERC20(name, symbol) Ownable() {
        _mint(msg.sender, mintAmount);
    }

    function mint(address receiver, uint amount) external onlyOwner {
        _mint(receiver, amount);
    }
}
