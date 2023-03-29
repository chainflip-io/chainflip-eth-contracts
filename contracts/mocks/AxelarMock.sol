// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

// Brownie scripts fail to import just an interface, so we need to create a mock contract.
contract AxelarGatewayMock {
    /**********\
    |* Errors *|
    \**********/

    error NotSelf();
    error NotProxy();
    error InvalidCodeHash();
    error SetupFailed();
    error InvalidAuthModule();
    error InvalidTokenDeployer();
    error InvalidAmount();
    error InvalidChainId();
    error InvalidCommands();
    error TokenDoesNotExist(string symbol);
    error TokenAlreadyExists(string symbol);
    error TokenDeployFailed(string symbol);
    error TokenContractDoesNotExist(address token);
    error BurnFailed(string symbol);
    error MintFailed(string symbol);
    error InvalidSetMintLimitsParams();
    error ExceedMintLimit(string symbol);

    /**********\
    |* Events *|
    \**********/

    event TokenSent(
        address indexed sender,
        string destinationChain,
        string destinationAddress,
        string symbol,
        uint256 amount
    );

    event ContractCall(
        address indexed sender,
        string destinationChain,
        string destinationContractAddress,
        bytes32 indexed payloadHash,
        bytes payload
    );

    event ContractCallWithToken(
        address indexed sender,
        string destinationChain,
        string destinationContractAddress,
        bytes32 indexed payloadHash,
        bytes payload,
        string symbol,
        uint256 amount
    );

    event Executed(bytes32 indexed commandId);

    event TokenDeployed(string symbol, address tokenAddresses);

    event ContractCallApproved(
        bytes32 indexed commandId,
        string sourceChain,
        string sourceAddress,
        address indexed contractAddress,
        bytes32 indexed payloadHash,
        bytes32 sourceTxHash,
        uint256 sourceEventIndex
    );

    event ContractCallApprovedWithMint(
        bytes32 indexed commandId,
        string sourceChain,
        string sourceAddress,
        address indexed contractAddress,
        bytes32 indexed payloadHash,
        string symbol,
        uint256 amount,
        bytes32 sourceTxHash,
        uint256 sourceEventIndex
    );

    event TokenMintLimitUpdated(string symbol, uint256 limit);

    event OperatorshipTransferred(bytes newOperatorsData);

    event Upgraded(address indexed implementation);

    /********************\
    |* Public Functions *|
    \********************/

    function sendToken(
        string calldata destinationChain,
        string calldata destinationAddress,
        string calldata symbol,
        uint256 amount
    ) external {}

    function callContract(
        string calldata destinationChain,
        string calldata contractAddress,
        bytes calldata payload
    ) external {}

    function callContractWithToken(
        string calldata destinationChain,
        string calldata contractAddress,
        bytes calldata payload,
        string calldata symbol,
        uint256 amount
    ) external {}

    function isContractCallApproved(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        address contractAddress,
        bytes32 payloadHash
    ) external view returns (bool) {}

    function isContractCallAndMintApproved(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        address contractAddress,
        bytes32 payloadHash,
        string calldata symbol,
        uint256 amount
    ) external view returns (bool) {}

    function validateContractCall(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes32 payloadHash
    ) external returns (bool) {}

    function validateContractCallAndMint(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes32 payloadHash,
        string calldata symbol,
        uint256 amount
    ) external returns (bool) {}

    /***********\
    |* Getters *|
    \***********/

    function authModule() external view returns (address) {}

    function tokenDeployer() external view returns (address) {}

    function tokenMintLimit(string memory symbol) external view returns (uint256) {}

    function tokenMintAmount(string memory symbol) external view returns (uint256) {}

    function allTokensFrozen() external view returns (bool) {}

    function implementation() external view returns (address) {}

    function tokenAddresses(string memory symbol) external view returns (address) {}

    function tokenFrozen(string memory symbol) external view returns (bool) {}

    function isCommandExecuted(bytes32 commandId) external view returns (bool) {}

    function adminEpoch() external view returns (uint256) {}

    function adminThreshold(uint256 epoch) external view returns (uint256) {}

    function admins(uint256 epoch) external view returns (address[] memory) {}

    /*******************\
    |* Admin Functions *|
    \*******************/

    function setTokenMintLimits(string[] calldata symbols, uint256[] calldata limits) external {}

    function upgrade(
        address newImplementation,
        bytes32 newImplementationCodeHash,
        bytes calldata setupParams
    ) external {}

    /**********************\
    |* External Functions *|
    \**********************/

    function setup(bytes calldata params) external {}

    function execute(bytes calldata input) external {}
}

contract AxelarGasService {
    error NothingReceived();
    error TransferFailed();
    error InvalidAddress();
    error NotCollector();
    error InvalidAmounts();

    event GasPaidForContractCall(
        address indexed sourceAddress,
        string destinationChain,
        string destinationAddress,
        bytes32 indexed payloadHash,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event GasPaidForContractCallWithToken(
        address indexed sourceAddress,
        string destinationChain,
        string destinationAddress,
        bytes32 indexed payloadHash,
        string symbol,
        uint256 amount,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event NativeGasPaidForContractCall(
        address indexed sourceAddress,
        string destinationChain,
        string destinationAddress,
        bytes32 indexed payloadHash,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event NativeGasPaidForContractCallWithToken(
        address indexed sourceAddress,
        string destinationChain,
        string destinationAddress,
        bytes32 indexed payloadHash,
        string symbol,
        uint256 amount,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event GasAdded(
        bytes32 indexed txHash,
        uint256 indexed logIndex,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event NativeGasAdded(bytes32 indexed txHash, uint256 indexed logIndex, uint256 gasFeeAmount, address refundAddress);

    // This is called on the source chain before calling the gateway to execute a remote contract.
    function payGasForContractCall(
        address sender,
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    ) external {}

    // TODO: This is causing a stack-to-deep error.
    // This is called on the source chain before calling the gateway to execute a remote contract.
    // function payGasForContractCallWithToken(
    //     address sender,
    //     string calldata destinationChain,
    //     string calldata destinationAddress,
    //     bytes calldata payload,
    //     string calldata symbol,
    //     uint256 amount,
    //     address gasToken,
    //     uint256 gasFeeAmount,
    //     address refundAddress
    // ) external {}

    // This is called on the source chain before calling the gateway to execute a remote contract.
    function payNativeGasForContractCall(
        address sender,
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        address refundAddress
    ) external payable {}

    // This is called on the source chain before calling the gateway to execute a remote contract.
    function payNativeGasForContractCallWithToken(
        address sender,
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        string calldata symbol,
        uint256 amount,
        address refundAddress
    ) external payable {}

    function addGas(
        bytes32 txHash,
        uint256 txIndex,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    ) external {}

    function addNativeGas(bytes32 txHash, uint256 logIndex, address refundAddress) external payable {}

    // function collectFees(address payable receiver, address[] calldata tokens, uint256[] calldata amounts) external {}

    // function refund(address payable receiver, address token, uint256 amount) external {}

    // function gasCollector() external returns (address) {}
}

// contract SquidRouter {
//     function executeWithToken(
//         bytes32 commandId,
//         string calldata sourceChain,
//         string calldata sourceAddress,
//         bytes calldata payload,
//         string calldata tokenSymbol,
//         uint256 amount
//     ) external {}
// }

// contract SimpleCallContract {
//     enum CallType {
//         Default,
//         FullTokenBalance,
//         FullNativeBalance,
//         CollectTokenBalance
//     }

//     struct Call {
//         CallType callType;
//         address target;
//         uint256 value;
//         bytes callData;
//         bytes payload;
//     }

//     function send(
//         string memory destinationChain,
//         string memory destinationContractAddress,
//         string memory symbol,
//         Call[] memory calls,
//         uint256 amount,
//         address gasReceiver,
//         address gateway,
//         address tokenAddress
//     ) external payable {
//         IERC20(tokenAddress).transferFrom(msg.sender, address(this), amount);
//         IERC20(tokenAddress).approve(address(gateway), amount);
//         bytes memory payload = encodeForSquid(calls, address(this));

//         // The line below is where we pay the gas fee
//         AxelarGasService(gasReceiver).payNativeGasForContractCallWithToken{value: msg.value}(
//             address(this),
//             destinationChain,
//             destinationContractAddress,
//             payload,
//             symbol,
//             amount,
//             msg.sender
//         );

//         AxelarGatewayMock(gateway).callContractWithToken(
//             destinationChain,
//             destinationContractAddress,
//             payload,
//             symbol,
//             amount
//         );
//     }

//     function encodeForSquid(Call[] memory calls, address a) public view returns (bytes memory) {
//         return abi.encode(calls, a);
//     }
// }
