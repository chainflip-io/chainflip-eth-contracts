pragma solidity ^0.8.0;

/**
 * @title    CF Receiver interface
 * @notice   The interface to recieve cross-message swaps + message call from the CF Vault.
 *           The received amount can be in the native token or in an ERC20 token.
 */
interface ICFReceiver {
    function cfRecieve(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable;

    function cfRecieveOnlyxCall(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) external;
}
