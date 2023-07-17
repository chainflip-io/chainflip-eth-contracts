import sys
from brownie import web3, chain, history
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
import json


def cleanHexStr(thing):
    if isinstance(thing, int):
        thing = hex(thing)
    elif not isinstance(thing, str):
        thing = thing.hex()
    return thing[2:] if thing[:2] == "0x" else thing


def hexStr(thing):
    thing = toHex(thing)
    return "0x" + thing


def toHex(thing):
    if isinstance(thing, int):
        thing = hex(thing)
    elif not isinstance(thing, str):
        thing = thing.hex()
    return thing


def cleanHexStrPad(thing):
    thing = cleanHexStr(thing)
    return ("0" * (64 - len(thing))) + thing


def getCreate2Addr(sender, saltHex, bytecode, argsHex):
    deployByteCode = bytecode + argsHex
    return web3.toChecksumAddress(
        web3.keccak(
            hexstr=(
                "ff"
                + cleanHexStr(sender)
                + saltHex
                + cleanHexStr(web3.keccak(hexstr=deployByteCode))
            )
        )[-20:].hex()
    )


def getKeyFromValue(dic, value):
    for key, val in dic.items():
        if val == value:
            return key


# Calculate pubKeyX and pubKeyYParity from the inputted aggKey
def getKeysFromAggKey(aggKey):
    parity = aggKey[0:2]
    x = aggKey[2:]
    parity = "00" if parity == "02" or parity == "00" else "01"
    return [int(x, 16), int(parity, 16)]


# This deletes elements in the lists inputted to the length of the shortest
# such that they're all the same length and returns the new lengths. The effect
# persists in the scope of whatever fcn calls trimToShortest since lists are a reference
def trimToShortest(lists):
    minLen = min(*[len(l) for l in lists])
    for l in lists:
        del l[minLen:]

    return minLen


def getValidTranIdxs(tokens, amounts, prevBal, tok):
    # Need to know which index that native transfers start to fail since they won't revert the tx, but won't send the expected amount
    cumulEthTran = 0
    validEthIdxs = []
    for i in range(len(tokens)):
        if tokens[i] == tok:
            if cumulEthTran + amounts[i] <= prevBal:
                validEthIdxs.append(i)
                cumulEthTran += amounts[i]

    return validEthIdxs


# EVM and local clock chain.time() are sometimes out of sync by 1, not sure
# why. Some tests occasionally fail for this reason even though they succeed most
# of the time with no changes to the contract or test code. Some testing seems to
# show that transactions are mined 1 later - so using chain.time()+1 as chain time.
def getChainTime():
    return chain.time() + 1


# Calculate gas spent by a particular address from the initialTransactionNumber onwards
# Not using all history because we might not want to include deployment/setup transactions
# Also, when testing with Rinkeby or a private blockchain, there might be previous
# transactions (that is not an issue when a local hardhat node is span every time)
# NOTE: in case of failure related to gas calculations, refer to comment in test_all invariant_bals.
def calculateGasSpentByAddress(address, initialTransactionNumber):
    # history.filter returns a list of all the broadcasted transactions (not necessarily mined)
    transactionList = history.filter(sender=address)[initialTransactionNumber:]
    nativeUsed = 0
    for txReceipt in transactionList:
        nativeUsed += calculateGasTransaction(txReceipt)
    return nativeUsed


# Calculate the gas spent in a single transaction
def calculateGasTransaction(txReceipt):
    # Might be necessary to wait for the transaction to be mined, especially in live networks that are slow.
    # Either check for status (txReceipt.status == 0 or == 1) or use wait_for_transaction_receipt.
    # web3.eth.wait_for_transaction_receipt(txReceipt.txid)

    # Gas calculation
    # Could be simplified with `txReceipt.gas_used * txReceipt.gas_price`, but keeping the calculation to show `base_fee + priority_fee`
    base_fee = web3.eth.get_block(txReceipt.block_number).baseFeePerGas
    priority_fee = txReceipt.gas_price - base_fee
    return (txReceipt.gas_used * base_fee) + (txReceipt.gas_used * priority_fee)


def get_contract_object(path_to_contract, address):
    ## path_to_contract from contracts folder. If a contract under the contracts folder, just the name of the contract.
    with open("build/contracts/" + path_to_contract + ".json") as f:
        info_json = json.load(f)
    abi = info_json["abi"]
    return web3.eth.contract(address=address, abi=abi)


# In order to get the event from a contract do "get_contract_object("contract_name", contract_address).events.event_name
def fetch_events(
    event,
    argument_filters=None,
    from_block=None,
    to_block="latest",
    address=None,
    topics=None,
):
    """Get events using eth_getLogs API.

    This is a stateless method, as opposite to createFilter and works with
    stateless nodes like QuikNode and Infura.

    :param event: Event instance from your contract.events
    :param argument_filters:
    :param from_block: Start block. Use 0 for all history/
    :param to_block: Fetch events until this contract
    :param address:
    :param topics:
    :return:
    """

    if from_block is None:
        raise TypeError("Missing mandatory keyword argument to getLogs: from_Block")

    abi = event._get_event_abi()
    abi_codec = event.web3.codec

    # Set up any indexed event filters if needed
    argument_filters = dict()
    _filters = dict(**argument_filters)

    data_filter_set, event_filter_params = construct_event_filter_params(
        abi,
        abi_codec,
        contract_address=event.address,
        argument_filters=_filters,
        fromBlock=from_block,
        toBlock=to_block,
        address=address,
        topics=topics,
    )

    # Call node over JSON-RPC API
    logs = event.web3.eth.get_logs(event_filter_params)

    # Convert raw binary event data to easily manipulable Python objects
    for entry in logs:
        data = get_event_data(abi_codec, abi, entry)
        yield data


def prompt_user_continue_or_break(prompt, default_yes):
    prompt_default = "([y]/n)" if default_yes else "(y/[n])"
    user_input = input("\n>> " + prompt + ". Continue? " + prompt_default + ": ")

    userInputConfirm = ["y", "Y", "yes", "Yes", "YES"]
    if default_yes:
        userInputConfirm.append("")

    if user_input not in userInputConfirm:
        ## Gracefully exit the script with a message.
        sys.exit("Cancelled by the user")
