from brownie import web3


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
    return web3.toChecksumAddress(web3.keccak(hexstr=("ff" + cleanHexStr(sender) + saltHex + cleanHexStr(web3.keccak(hexstr=deployByteCode))))[-20:].hex())


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

# We can't actually refund _everything_ because gas is so weird. But we can
# refund most of it, so we should check here that the balance is above what we
# would expect it to be if there was no refund, but below or equal to the
# balanceBefore (we know the Validator has not got more than they should)
def txRefundTest(balanceBefore, balanceAfter, tx):
    base_fee = web3.eth.get_block(tx.block_number).baseFeePerGas

    # this is set in the tests earlier, (deploy.py) but we might as well
    # calculate it here so we only have to update it once
    priority_fee = tx.gas_price - base_fee

    ethUsed = (tx.gas_used * base_fee) + (tx.gas_used * priority_fee)
    totalRefunded = tx.events["Refunded"][0].values()[0]
    assert balanceAfter <= balanceBefore
    assert balanceAfter >= balanceBefore - ethUsed
    return totalRefunded

# Test with timestamp-1 because of an error where there's a difference of 1s
# because the evm and local clock were out of sync or something... not 100% sure why,
# but some tests occasionally fail for this reason even though they succeed most
# of the time with no changes to the contract or test code
def txTimeTest(time, tx):
    assert time >= tx.timestamp and time <= (tx.timestamp+2)