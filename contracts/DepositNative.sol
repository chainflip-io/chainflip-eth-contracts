pragma solidity ^0.8.0;

/**
 * @title    DepositNative contract
 * @notice   Creates a contract with a known address and withdraws all the native tokens from
 *           it before destroying itself and refunding some native tokens.
 */
contract DepositNative {
    constructor() {
        // This contract should only have been created if there's
        // already enough native tokens here. This will also send any excess
        // that the user mistakenly sent
        selfdestruct(payable(msg.sender));
    }
}
