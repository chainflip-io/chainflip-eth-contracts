from brownie import web3, chain, history
import time


def cleanHexStr(thing):
    if isinstance(thing, int):
        thing = hex(thing)
    elif not isinstance(thing, str):
        thing = thing.hex()
    return thing[2:] if thing[:2] == "0x" else thing


def cleanHexStrPad(thing):
    thing = cleanHexStr(thing)
    return ("0" * (64 - len(thing))) + thing


def getCreate2Addr(sender, saltHex, contractContainer, argsHex):
    deployByteCode = contractContainer.bytecode + argsHex
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


def getInflation(prevBlockNum, curBlockNum, emissionRate):
    return (curBlockNum - prevBlockNum) * emissionRate


def getKeyFromValue(dic, value):
    for key, val in dic.items():
        if val == value:
            return key


# This deletes elements in the lists inputted to the length of the shortest
# such that they're all the same length and returns the new lengths. The effect
# persists in the scope of whatever fcn calls trimToShortest since lists are a reference
def trimToShortest(lists):
    minLen = min(*[len(l) for l in lists])
    for l in lists:
        del l[minLen:]

    return minLen


def null_sig(nonce):
    return (0, 0, nonce)


def getValidTranIdxs(tokens, amounts, prevBal, tok):
    # Need to know which index that ETH transfers start to fail since they won't revert the tx, but won't send the expected amount
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
def calculateGasSpentByAddress(address, initialTransactionNumber):
    # history.filter returns a list of all the broadcasted transactions (not necessarily mined)
    transactionList = history.filter(sender=address)[initialTransactionNumber:]
    ethUsed = 0
    for txReceipt in transactionList:
        ethUsed += calculateGasTransaction(txReceipt)
    return ethUsed


# Calculate the gas spent in a single transaction
def calculateGasTransaction(txReceipt):
    # Might be necessary to wait for the transaction to be mined (txReceipt.status == 0 or == 1). Especially
    # in live networks that are slow.
    # web3.eth.wait_for_transaction_receipt(txReceipt.txid)

    # Error in test_all - calculateGasSpentByAddress seems to be smaller than expected and intermittently the eth balance assertion
    # fails. Could be that the tx gas values are off or that brownie and/or history.filter has a bug and doesn't report all the
    # sent transactions. Adding a sleep at test_all seems to improve the situation, so the latter one seems more likely. Also, it
    # is an error that only occurs at the end of a test, so it is unlikely that the calculations are wrong or that we need to add
    # the wait_for_transaction_receipt before doing the calculation.

    # Adding a time.sleep(1) in the invariant_bals in test_all and wait_for_transaction_receipt (which I suspect is effectively
    # only acting as a delay) seems to not be good enough, but it improves a lot (14/15 pass)
    # time.sleep(2) has not improved it though.

    # Adding a time.sleep(3) in the invariant_bals in test_all seems to make all runs pass

    # Gas calculation
    # Could be simplified with `txReceipt.gas_used * txReceipt.gas_price`, but keeping the calculation to show `base_fee + priority_fee`
    base_fee = web3.eth.get_block(txReceipt.block_number).baseFeePerGas
    priority_fee = txReceipt.gas_price - base_fee
    return (txReceipt.gas_used * base_fee) + (txReceipt.gas_used * priority_fee)
