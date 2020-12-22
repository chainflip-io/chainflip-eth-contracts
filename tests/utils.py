from brownie import web3 as w3


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
    print(f'deployByteCode = {deployByteCode}')
    return w3.keccak(hexstr=("ff" + cleanHexStr(sender) + saltHex + cleanHexStr(w3.keccak(hexstr=deployByteCode))))[-20:].hex()
