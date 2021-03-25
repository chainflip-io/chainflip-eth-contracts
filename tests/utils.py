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


def trimToShortest(lists):
    minLen = min(*[len(l) for l in lists])
    for l in lists:
        del l[minLen:]
    
    return minLen