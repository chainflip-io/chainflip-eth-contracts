pragma solidity ^0.8.0;


// Have to use this contract because of a difference in rounding errors
// between Solidity and Python
contract MockMaths {
    function simulateRelease(uint total, uint time, uint start, uint end, uint cliff) external pure returns (uint) {
        uint256 cliffAmount = total / 5;
        return cliffAmount + (total - cliffAmount)  * (time - cliff) / (end - cliff);

    }
}