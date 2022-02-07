pragma solidity ^0.8.0;


// Have to use this contract because of a difference in rounding errors
// between Solidity and Python
contract MockMaths {
    function simulateRelease(uint total, uint time, uint start, uint end) external pure returns (uint) {
        return total * (time - start) / (end - start);
    }
}