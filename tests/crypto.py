from utils import *
from brownie import chain
import umbral
from umbral import SecretKey
from py_ecc.secp256k1 import secp256k1
from eth_abi import encode_abi
from brownie.convert import to_bytes
from brownie.convert.utils import get_type_strings
from brownie.convert.normalize import format_input
import copy

# Fcns return a list instead of a tuple since they need to be modified
# for some tests (e.g. to make them revert)
class Signer:

    Q = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141"
    Q_INT = int(Q, 16)
    HALF_Q_INT = (Q_INT >> 1) + 1
    AGG = "Agg"

    def __init__(self, privKeyHex, keyID, nonces):
        self.privKeyHex = privKeyHex
        self.privKey = SecretKey._from_exact_bytes(bytes.fromhex(privKeyHex))
        self.privKeyInt = int(self.privKeyHex, 16)

        self.pubKey = self.privKey.public_key()
        self.pubKeyX = bytes(self.pubKey)[1:]
        self.pubKeyXHex = cleanHexStr(self.pubKeyX)
        self.pubKeyXInt = int(self.pubKeyXHex, 16)

        self.pubKeyYPar = 0 if cleanHexStr(bytes(self.pubKey)[:1]) == "02" else 1
        self.pubKeyYParHex = "00" if self.pubKeyYPar == 0 else "01"

        self.nonces = nonces

    @cla.scgethod
    def priv_key_to_pubX_int(cls, privKey):
        pubKey = privKey.public_key()
        pubKeyX = bytes(pubKey)[1:]
        return int(cleanHexStr(pubKeyX), 16)

    @cla.scgethod
    def gen_key(cls):
        key = SecretKey.random()
        while cls.priv_key_to_pubX_int(key) >= cls.HALF_Q_INT:
            key = SecretKey.random()

        return key

    @cla.scgethod
    def gen_key_hex(cls):
        return cls.gen_key().to_secret_bytes().hex()

    @cla.scgethod
    def gen_signer(cls, keyID, nonces):
        privKeyHex = cls.gen_key_hex()
        return cls(privKeyHex, keyID, nonces)

    def getPubData(self):
        return [self.pubKeyXInt, self.pubKeyYPar]

    def getPubDataWith0x(self):
        return [self.pubKeyXInt, self.pubKeyYPar]

    def getSigData(self, keyManager, fcn, *args):
        return self.getSigDataWithNonces(keyManager, fcn, self.nonces, *args)

    def getSigDataWithNonces(self, keyManager, fcn, nonces, *args):
        # Get the nonceConsumer's address that will make the call to verify the signature
        nonceConsumerAddress = fcn._address

        contractMsgHash = Signer.generate_contractMsgHash(fcn, *args)

        msgHash = Signer.generate_msgHash(
            contractMsgHash, nonces, keyManager.address, nonceConsumerAddress
        )
        # Return sigData
        return self.generate_sigData(msgHash, nonces)

    def generate_sigData(self, msgHash, nonces):

        [s, nonceTimesGeneratorAddress] = self.sign(msgHash)
        sigData = [
            s,
            nonces[self.AGG],
            nonceTimesGeneratorAddress,
        ]

        # Since nonces is passed by reference, it will be altered for all other signers too
        nonces[self.AGG] += 1
        return sigData

    # Generate the contractMsgHash by hashing the function selector and the function arguments
    @staticmethod
    def generate_contractMsgHash(fcn, *args):
        # Health check - function arguments contains an extra sigData
        assert len(fcn.abi["inputs"]) == len(args) + 1

        # Get the function selector signature
        fcnSig = fcn.signature
        fcnSig = to_bytes(fcnSig, "bytes4")

        # Get the function types from the abi
        types = get_type_strings(fcn.abi["inputs"])

        # Replace the first parameter (sigData) for the selector
        type_fcnSig = "bytes4"
        assert types[0] == "(uint256,uint256,address)"
        types[0] = type_fcnSig

        # Format inputs according to abi, otherwise brownie accounts fail to be understood as addresses
        # Remove sigData input to match args. We need to first remove sigData
        modified_abi = copy.deepcopy(fcn.abi)
        # Remove sigData type
        modified_abi["inputs"].pop(0)
        formatted_args = format_input(modified_abi, args)

        contractMsgToHash = encode_abi(types, [fcnSig, *formatted_args])
        return web3.keccak(contractMsgToHash)

    # Generate the msgHash by hashing the contractMsgHash, the nonces, the keyManager address and the chainID
    @staticmethod
    def generate_msgHash(
        contractMsgHash, nonces, keyManagerAddress, nonceConsumerAddress, **kwargs
    ):
        chainId = kwargs.get("chainId", chain.id)

        # Format inputs according to abi, otherwise brownie accounts fail to be understood as addresses
        aux_abi = {
            "inputs": [
                {"type": "bytes32"},
                {"type": "uint256"},
                {"type": "address"},
                {"type": "uint256"},
                {"type": "address"},
            ]
        }
        args = [
            contractMsgHash,
            nonces["Agg"],
            nonceConsumerAddress,
            chainId,
            keyManagerAddress,
        ]
        formatted_args = format_input(aux_abi, args)

        # msgToHash will be in hex format (HexBytes('0x8ce..'))
        msgToHash = encode_abi(
            ["bytes32", "uint256", "address", "uint256", "address"],
            formatted_args,
        )

        # No need for "hexstr="" as msgToHash a hex byte obj
        return cleanHexStr(web3.keccak(msgToHash))

    # @dev reference /contracts/abstract/SchnorrSECP256k1.sol
    def sign(self, msgHashHex):
        # Pick a "random" nonce (k)
        k = int(web3.keccak(hexstr=msgHashHex).hex(), 16)
        kTimesG = tuple(secp256k1.multiply(secp256k1.G, k))

        # Get the x and y ordinate of our k*G value
        kTimesGXInt = kTimesG[0]
        kTimesGYInt = kTimesG[1]
        kTimesGXBytes = (kTimesGXInt).to_bytes(32, byteorder="big")
        kTimesGYParityBytes = (kTimesGYInt).to_bytes(32, byteorder="big")
        kTimesGConcat = kTimesGXBytes + kTimesGYParityBytes

        # Get the hash of the concatenated (uncompressed) key
        k256 = web3.keccak(kTimesGConcat)

        # Get the last 20 bytes of the hash, which is Ethereum Address format
        nonceTimesGeneratorAddress = web3.toChecksumAddress(cleanHexStr(k256)[-40:])

        challengeEncodedPacked = (
            cleanHexStrPad(self.pubKeyX)
            + self.pubKeyYParHex
            + cleanHexStr(msgHashHex)
            + cleanHexStr(nonceTimesGeneratorAddress)
        )

        e = web3.keccak(hexstr=challengeEncodedPacked)
        eInt = int(cleanHexStr(e), 16)

        s = (k - (self.privKeyInt * eInt)) % self.Q_INT
        s = s + self.Q_INT if s < 0 else s

        return [s, nonceTimesGeneratorAddress]
