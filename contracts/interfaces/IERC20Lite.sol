pragma solidity ^0.7.0;


interface IERC20Lite {
    function transfer(address, uint256) external returns (bool);
    function balanceOf(address) external returns(uint);
}