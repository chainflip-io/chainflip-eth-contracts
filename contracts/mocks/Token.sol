pragma solidity ^0.8.6;


import "@openzeppelin/contracts/token/ERC20/ERC20.sol";


/**
* @title    Token
* @dev      Creates a standard ERC20 just for the purposes of testing
* @author   Quantaf1re (James Key)
*/
contract Token is ERC20 {
    constructor (string memory name, string memory symbol, uint256 mintAmount) ERC20(name, symbol) {
        _mint(msg.sender, mintAmount);
    }
}