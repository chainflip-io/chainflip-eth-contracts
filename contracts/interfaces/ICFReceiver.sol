pragma solidity ^0.8.0;

/**
 * @title    CF Receiver interface
 * @notice   The interface to recieve cross-message swaps + message call from the CF Vault.
 *           The received amount can be in the native token or in an ERC20 token.
 */
interface ICFReceiver {
    function cfRecieve(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable;

    function cfRecievexCall(
        uint32 srcChain,
        string calldata srcAddress,
        bytes calldata message
    ) external;
}
