// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/// @dev Contract that forces native tokens to an address. This is only for testing purposes.
contract ForceNativeTokens {
    constructor(address payable recipient) payable {
        selfdestruct(recipient);
    }
}
