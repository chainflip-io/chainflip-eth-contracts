pragma solidity ^0.8.7;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title    FLIP interface for the FLIP utility token
 * @author   Quantaf1re (James Key)
 */
interface IFLIP is IERC20 {
    function mint(
        address receiver,
        uint256 amount
    ) external;
}
