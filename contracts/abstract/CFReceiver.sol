pragma solidity ^0.8.0;

import "../interfaces/ICFReceiver.sol";

/**
 * @title    CFReceiver
 * @dev      Receives cross-chain messages and tokens coming from the Chainflip Protocol.
 *           The ICFReceiver interface is the interface required to recieve tokens and
 *           messages from the Chainflip Protocol. This contract checks that the sender is
 *           the Chainflip Vault.
 *           CF ensures that the reciever will be receving the amount of tokens passed as
 *           parameters. However, anyone can bridge tokens to the reciever contract. Also,
 *           if msg.sender is not checked it could be any external call that is not really
 *           transferring the tokens before making the call. So an extra check of the
 *           srcAddress is adviced to be done in the _cfRceive* function.
 *           In the case of receiving ETH, the user could instead check that msg.value
 *           is equal to the amount passed as parameter.
 */

abstract contract CFReceiver is ICFReceiver {
    /// @dev    Chainflip's Vault address where xSwaps and xCalls will be originated from.
    address public _cfSender;

    constructor(address cfSender) {
        _cfSender = cfSender;
    }

    function cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable override onlyCFSender {
        _cfRecieve(srcChain, srcAddress, message, token, amount);
    }

    function cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) external override onlyCFSender {
        _cfRecievexCall(srcChain, srcAddress, message);
    }

    function _cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal virtual;

    function _cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) internal virtual;

    modifier onlyCFSender() {
        require(msg.sender == _cfSender, "CFReceiver: caller not Chainflips sender");
        _;
    }
}
