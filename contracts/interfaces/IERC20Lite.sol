pragma solidity ^0.8.0;


/**
* @title    ERC20 Interface
* @notice   The interface for functions ERC20Lite implements. This is intended to
*           be used with DepositEth so that there is as little code that goes into
*           it as possible to reduce gas costs since it'll be deployed frequently
* @author   Quantaf1re (James Key)
*/
interface IERC20Lite {
    function transfer(address, uint256) external returns (bool);
    function balanceOf(address) external returns(uint);
}