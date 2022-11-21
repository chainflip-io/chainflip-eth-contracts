pragma solidity ^0.8.0;

import "./interfaces/ICFReceiver.sol";

/**
 * @title    CFReceiver
 * @dev      Receives cross-chain messages and tokens coming from the Chainflip Protocol.
 *           The ICFReceiver interface is the interface required to recieve tokens and
 *           messages from the Chainflip Protocol. This contract checks that the sender is
 *           the Chainflip Vault.
 *           CF ensures that the reciever will be receving the amount of tokens passed as
 *           parameters. However, anyone can bridge tokens to the reciever contract. So
 *           an extra check of the ingressAddress shall be done in the _cfRceive function.
 */

contract CFReceiver is ICFReceiver {
    address private _cfSender;

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

    function cfRecieveOnlyXCall(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) external override onlyCFSender {
        _cfRecieveOnlyXCall(ingressParams, ingressAddress, message);
    }

    function _cfRecieve(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal virtual {}

    function _cfRecieveOnlyXCall(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) internal virtual {}

    modifier onlyCFSender() {
        require(msg.sender == _cfSender, "CFReceiver: caller is not the CF Sender");
        _;
    }
}
