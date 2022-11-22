pragma solidity ^0.8.0;

import "./interfaces/ICFReceiver.sol";

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
 *           ingressAddress is adviced to be done in the _cfRceive* function.
 *           In the case of receiving ETH, the user could instead check that msg.value
 *           is equal to the amount passed as parameter.
 */

contract CFReceiver is ICFReceiver {
    /// @dev    Chainflip's Vault address where xCalls will be sent.
    address public _cfSender;

    constructor(address cfSender) {
        _cfSender = cfSender;
    }

    function cfRecieve(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable override onlyCFSender {
        _cfRecieve(ingressParams, ingressAddress, message, token, amount);
    }

    function cfRecieveOnlyxCall(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) external override onlyCFSender {
        _cfRecieveOnlyxCall(ingressParams, ingressAddress, message);
    }

    function _cfRecieve(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal virtual {}

    function _cfRecieveOnlyxCall(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) internal virtual {}

    modifier onlyCFSender() {
        require(msg.sender == _cfSender, "CFReceiver: caller is not the CF Sender");
        _;
    }
}
