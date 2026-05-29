// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @dev Required by TronBox's test runner for migration tracking.
contract Migrations {
    address public owner;
    // solhint-disable-next-line var-name-mixedcase
    uint256 public last_completed_migration;

    modifier restricted() {
        require(msg.sender == owner, "restricted");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setCompleted(uint256 completed) public restricted {
        last_completed_migration = completed;
    }
}
