pragma solidity ^0.8.0;

import "../interfaces/ICFReceiver.sol";

/**
 * @title    CFReceiver
 * @dev      This abstract contract is the base implementation for a smart contract
 *           capable of receiving cross-chain swaps and calls from the Chainflip Protocol.
 *           It has a check to ensure that the functions can only be called by one
 *           address, which should be the Chainflip Protocol. This way it is ensured that
 *           the receiver will be sent the amount of tokens passed as parameters and
 *           that the cross-chain call originates from the srcChain and address specified.
 *           This contract should be inherited and then user's logic should be implemented
 *           as the internal functions (_cfReceive and _cfReceivexCall).
 *           Remember that anyone on the source chain can use the Chainflip Protocol
 *           to make a cross-chain call to this contract. If that is not desired, an extra
 *           check on the source address and source chain should be performed.
 */

abstract contract CFReceiver is ICFReceiver {
    /// @dev    Chainflip's Vault address where xSwaps and xCalls will be originated from.
    address public _cfVault;

    constructor(address cfVault) {
        _cfVault = cfVault;
    }

    /// @dev Receiver of a cross-chain swap and call.
    function cfReceive(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable override onlyCfVault {
        _cfReceive(srcChain, srcAddress, message, token, amount);
    }

    /// @dev Receiver of a cross-chain call.
    function cfReceivexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) external override onlyCfVault {
        _cfReceivexCall(srcChain, srcAddress, message);
    }

    /// @dev Internal function to be overriden by the user's logic.
    function _cfReceive(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal virtual;

    /// @dev Internal function to be overriden by the user's logic.
    function _cfReceivexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal virtual;

    /// @dev Check that the sender is the Chainflip's Vault.
    modifier onlyCfVault() {
        require(msg.sender == _cfVault, "CFReceiver: caller not Chainflip sender");
        _;
    }
}
