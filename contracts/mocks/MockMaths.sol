pragma solidity ^0.8.0;

// Have to use this contract because of a difference in rounding errors
// between Solidity and Python
contract MockMaths {
    function simulateRelease(
        uint256 total,
        uint256 time,
        uint256 start,
        uint256 end,
        uint256 cliff
    ) external pure returns (uint256) {
        uint256 cliffAmount = total / 5;
        return cliffAmount + (total - cliffAmount)  * (time - cliff) / (end - cliff);
    }
}
