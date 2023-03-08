pragma solidity ^0.8.0;

// Brownie needs a contract to be able to encode the inputs, the interface is not enough.
// We can probably import the real contracts instead, this is just a quick fix.
contract TokenMessengerMock {
    event DepositForBurn(
        uint64 indexed nonce,
        address indexed burnToken,
        uint256 amount,
        address indexed depositor,
        bytes32 mintRecipient,
        uint32 destinationDomain,
        bytes32 destinationTokenMessenger,
        bytes32 destinationCaller
    );

    event MessageSent(bytes message);

    function depositForBurn(
        uint256 amount,
        uint32 destinationDomain,
        bytes32 mintRecipient,
        address burnToken
    ) external {
        // emits DepositForBurn & MessageSent
    }

    event MessageReceived(
        address indexed caller,
        uint32 sourceDomain,
        uint64 indexed nonce,
        bytes32 sender,
        bytes messageBody
    );

    event MintAndWithdraw(address indexed mintRecipient, uint256 amount, address indexed mintToken);

    function receiveMessage(bytes calldata message, bytes calldata attestation) external returns (bool success) {
        // MessageTransmitter Emits MessageReceived
        // USDC contract will emit mint to recipient
        // TokenMessenger also emits MintAndWithdraw
    }
}
