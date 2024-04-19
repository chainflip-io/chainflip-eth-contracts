import sys
import os

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import accounts, Contract, web3

# Original from Arbitrum code:
# https://github.com/OffchainLabs/arbitrum-tutorials/blob/master/packages/gas-estimation/scripts/exec.ts

REFERENCE_GAS_LIMIT = 21004


def gas_estimate_component():
    nodeInterface = Contract.from_abi(
        "NodeInterface", "0x00000000000000000000000000000000000000C8", nodeInterfaceAbi
    )

    # Address where the transaction being estimated will be sent
    destinationAddress = ZERO_ADDR

    # The input data of the transaction, in hex.
    # txData = "1234567890abcdef1234" * 100 # 1000 bytes
    # Real CCM call with message = 100 bytes => Results in ~bytes
    # txData = "5293178ea596bb6cbd983189b6ad3d11a695ecf24de2eead6fb79ff3b4ae017920ce39d20000000000000000000000000000000000000000000000000000000000000009000000000000000000000000396b485f65eb400cc84e534ab2645e77353eeef8000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee0000000000000000000000009fe46736679d2d9a65f0992f2272de9f3c7fa6e000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000012000000000000000000000000000000000000000000000000000000000000001600000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000640000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    txData = ""

    gasEstimateComponents = nodeInterface.gasEstimateComponents.call(
        destinationAddress, False, txData
    )
    print("gasEstimateComponents", gasEstimateComponents)

    # Getting useful values for calculating the formula
    gasEstimate = gasEstimateComponents[0]
    gasEstimateForL1 = gasEstimateComponents[1]
    baseFee = gasEstimateComponents[2]
    l1BaseFeeEstimate = gasEstimateComponents[3]

    # Script naming
    l1GasEstimated = gasEstimateForL1
    l2GasUsed = gasEstimate - gasEstimateForL1
    l2EstimatedPrice = baseFee
    l1EstimatedPrice = l1BaseFeeEstimate * 16

    l1Cost = l1GasEstimated * l2EstimatedPrice
    l1Size = l1Cost / l1EstimatedPrice if l1EstimatedPrice != 0 else 0

    P = l2EstimatedPrice
    L2G = l2GasUsed
    L1P = l1EstimatedPrice
    L1S = l1Size

    # L1C (L1 Cost) = L1P * L1S
    L1C = L1P * L1S

    # B (Extra Buffer) = L1C / P
    B = L1C / P if P != 0 else 0

    # G (Gas Limit) = L2G + B
    G = L2G + B

    # TXFEES (Transaction fees) = P * G
    TXFEES = P * G

    print("Gas estimation components")
    print("-------------------")
    print("Full gas estimation = ", gasEstimate, "units")
    print("L2 Gas (L2G) = ", L2G, "units")
    print("L1 estimated Gas (L1G) = ", l1GasEstimated, "units")

    print("P (L2 Gas Price) = ", P)
    print("L1P (L1 estimated calldata price per byte) = ", L1P)
    print("L1S (L1 Calldata size in bytes) =", L1S, "bytes")

    print("-------------------")
    print("Transaction estimated fees to pay =", TXFEES)

    # I think what we want to use to track is G, aka the gas limit. however, this ends up
    # being the same as the gas estimation, so we can just use the gas estimation as a proxy.
    print("Gas Limit", G, "units")
    print("Buffer", B, "units")

    # Only gotcha is that it will depend on the lenght of the data for CCM calls. The gas limit
    # will increment according to:
    # G = L2G + B = L2G + (L1 calldata cost) / P => L1P is the same, P is the same, L2G increases and L1S increases.
    # That would increase with L2G < x < L1G + L2G
    print("Factor:", G / REFERENCE_GAS_LIMIT)


def get_fee_history():
    print(
        "Ethereum base fee queryied        ",
        web3.eth.fee_history(1, "latest", [0.5]).baseFeePerGas[0],
    )


def estimate_gas():
    print(
        "estimate gas",
        web3.eth.estimate_gas(
            {
                "to": ZERO_ADDR,
                "from": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
                "value": 12345,
                "data": "0x123137548635386",
            }
        ),
    )


nodeInterfaceAbi = [
    {
        "inputs": [
            {"internalType": "uint64", "name": "size", "type": "uint64"},
            {"internalType": "uint64", "name": "leaf", "type": "uint64"},
        ],
        "name": "constructOutboxProof",
        "outputs": [
            {"internalType": "bytes32", "name": "send", "type": "bytes32"},
            {"internalType": "bytes32", "name": "root", "type": "bytes32"},
            {"internalType": "bytes32[]", "name": "proof", "type": "bytes32[]"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "sender", "type": "address"},
            {"internalType": "uint256", "name": "deposit", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "l2CallValue", "type": "uint256"},
            {
                "internalType": "address",
                "name": "excessFeeRefundAddress",
                "type": "address",
            },
            {
                "internalType": "address",
                "name": "callValueRefundAddress",
                "type": "address",
            },
            {"internalType": "bytes", "name": "data", "type": "bytes"},
        ],
        "name": "estimateRetryableTicket",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint64", "name": "blockNum", "type": "uint64"}],
        "name": "findBatchContainingBlock",
        "outputs": [{"internalType": "uint64", "name": "batch", "type": "uint64"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "bool", "name": "contractCreation", "type": "bool"},
            {"internalType": "bytes", "name": "data", "type": "bytes"},
        ],
        "name": "gasEstimateComponents",
        "outputs": [
            {"internalType": "uint64", "name": "gasEstimate", "type": "uint64"},
            {"internalType": "uint64", "name": "gasEstimateForL1", "type": "uint64"},
            {"internalType": "uint256", "name": "baseFee", "type": "uint256"},
            {"internalType": "uint256", "name": "l1BaseFeeEstimate", "type": "uint256"},
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "bool", "name": "contractCreation", "type": "bool"},
            {"internalType": "bytes", "name": "data", "type": "bytes"},
        ],
        "name": "gasEstimateL1Component",
        "outputs": [
            {"internalType": "uint64", "name": "gasEstimateForL1", "type": "uint64"},
            {"internalType": "uint256", "name": "baseFee", "type": "uint256"},
            {"internalType": "uint256", "name": "l1BaseFeeEstimate", "type": "uint256"},
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "blockHash", "type": "bytes32"}],
        "name": "getL1Confirmations",
        "outputs": [
            {"internalType": "uint64", "name": "confirmations", "type": "uint64"}
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "batchNum", "type": "uint256"},
            {"internalType": "uint64", "name": "index", "type": "uint64"},
        ],
        "name": "legacyLookupMessageBatchProof",
        "outputs": [
            {"internalType": "bytes32[]", "name": "proof", "type": "bytes32[]"},
            {"internalType": "uint256", "name": "path", "type": "uint256"},
            {"internalType": "address", "name": "l2Sender", "type": "address"},
            {"internalType": "address", "name": "l1Dest", "type": "address"},
            {"internalType": "uint256", "name": "l2Block", "type": "uint256"},
            {"internalType": "uint256", "name": "l1Block", "type": "uint256"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "bytes", "name": "calldataForL1", "type": "bytes"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "nitroGenesisBlock",
        "outputs": [{"internalType": "uint256", "name": "number", "type": "uint256"}],
        "stateMutability": "pure",
        "type": "function",
    },
]
