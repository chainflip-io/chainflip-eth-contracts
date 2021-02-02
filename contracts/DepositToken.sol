pragma solidity ^0.7.0;


import "./interfaces/IERC20Lite.sol";


/**
* @title    DepositToken contract
* @notice   Creates a contract with a known address and withdraws tokens (and ETH) from it
* @author   Quantaf1re (James Key)
*/
contract DepositToken {

    constructor(address token) {
        IERC20Lite(token).transfer(msg.sender, IERC20Lite(token).balanceOf(address(this)));
        // This will also send any excess ETH that the user mistakenly sent
        selfdestruct(msg.sender);
    }

}