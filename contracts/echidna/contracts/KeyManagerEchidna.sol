pragma solidity ^0.8.0;

import "../../interfaces/IShared.sol";
import "../../interfaces/IKeyManager.sol";

contract KeyManagerEchidna is IShared {
    IKeyManager public km;

    // Expose KeyManager functions to Echidna - making them virtual to override them in tests when needed

    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) external virtual {
        km.consumeKeyNonce(sigData, contractMsgHash);
    }

    function setAggKeyWithAggKey(SigData calldata sigData, Key calldata newAggKey) external virtual {
        km.setAggKeyWithAggKey(sigData, newAggKey);
    }

    function setGovKeyWithAggKey(SigData calldata sigData, address newGovKey) external virtual {
        km.setGovKeyWithAggKey(sigData, newGovKey);
    }

    function setGovKeyWithGovKey(address newGovKey) external virtual {
        km.setGovKeyWithGovKey(newGovKey);
    }

    function setCommKeyWithAggKey(SigData calldata sigData, address newCommKey) external virtual {
        km.setCommKeyWithAggKey(sigData, newCommKey);
    }

    function setCommKeyWithCommKey(address newCommKey) external virtual {
        km.setCommKeyWithCommKey(newCommKey);
    }

    function govAction(bytes32 message) external virtual {
        km.govAction(message);
    }

    // Comparing with abi.encodePacked as that is what SchnorrSECP256K1 uses the msgHash for
    function encodingBytes_verifySig(
        bytes32 msgHash,
        uint256 signature,
        uint256 signingPubKeyX,
        uint8 pubKeyYParity,
        address nonceTimesGeneratorAddress
    ) external virtual {
        assert(
            uint256(keccak256(abi.encodePacked(signingPubKeyX, pubKeyYParity, msgHash, nonceTimesGeneratorAddress))) ==
                uint256(
                    keccak256(
                        abi.encodePacked(signingPubKeyX, pubKeyYParity, uint256(msgHash), nonceTimesGeneratorAddress)
                    )
                )
        );
    }
}
