pragma solidity ^0.8.0;

/**
 * @title    CF Receiver interface
 * @notice   The interface to recieve cross-message calls from the CF Vault.
 */
interface ICFReceiver {
    function cfRecieve(
        string calldata ingressChain,
        string calldata ingressAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external;

    function cfRecieveMessage(
        string calldata ingressChain,
        string calldata ingressAddress,
        bytes calldata message
    ) external;
}

// Should we add a cF Receive function that checks that the source is the Vault?
// I don't think we can implement this (check what the other protocol does) but we
// can add a comment that tells the user to have that on their side.
