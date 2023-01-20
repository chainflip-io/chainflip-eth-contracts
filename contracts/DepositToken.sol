pragma solidity ^0.8.0;

import "./interfaces/IERC20Lite.sol";

/**
 * @title    DepositToken contract
 * @notice   Creates a contract with a known address and withdraws tokens (and native) from it
 *           before destroying itself and refunding some native tokens.
 */
contract DepositToken {
    constructor(IERC20Lite token) {
        // SafeTransfer not used because the CFE should only fetch this deposit if
        // the coins are already in this contract, and adding library logic would
        // increase gas costs of deploying the contract quite a bit
        require(token.transfer(msg.sender, token.balanceOf(address(this))), "DepositToken: transfer failed");
        // This will also send any excess native tokens that the user mistakenly sent
        selfdestruct(payable(msg.sender));
    }
}
