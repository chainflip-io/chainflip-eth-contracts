pragma solidity ^0.7.0;


import "OpenZeppelin/openzeppelin-contracts@3.3.0-solc-0.7/contracts/token/ERC20/ERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@3.3.0-solc-0.7/contracts/access/Ownable.sol";


contract FLIP is ERC20, Ownable {
    
    constructor (string memory name, string memory symbol, uint256 mintAmount) ERC20(name, symbol) Ownable() {
        _mint(msg.sender, mintAmount);
    }
}