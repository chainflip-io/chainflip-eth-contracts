pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title    Token
 * @dev      Creates a mock USDC contract just for the internal ETH network testing
 */
contract MockUSDC is ERC20 {
    constructor(
        string memory name,
        string memory symbol,
        uint256 mintAmount
    ) ERC20(name, symbol) {
        _mint(msg.sender, mintAmount);
    }

	function decimals() public view override returns (uint8) {
		return 6;
	}    
}
