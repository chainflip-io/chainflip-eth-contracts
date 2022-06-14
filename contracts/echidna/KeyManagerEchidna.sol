pragma solidity ^0.8.0;

import "../interfaces/IShared.sol";
import "../interfaces/IKeyManager.sol";

contract KeyManagerEchidna is IShared {
    IKeyManager public km;

    // Expose KeyManager functions to Echidna

    function setCanConsumeKeyNonce(address[] calldata addrs) external {
        km.setCanConsumeKeyNonce(addrs);
    }

    function updateCanConsumeKeyNonce(
        SigData calldata sigData,
        address[] calldata currentAddrs,
        address[] calldata newAddrs
    ) external {
        km.updateCanConsumeKeyNonce(sigData, currentAddrs, newAddrs);
    }

    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) external {
        km.consumeKeyNonce(sigData, contractMsgHash);
    }

    function setAggKeyWithAggKey(SigData calldata sigData, Key calldata newAggKey) external {
        km.setAggKeyWithAggKey(sigData, newAggKey);
    }

    function setGovKeyWithAggKey(SigData calldata sigData, address newGovKey) external {
        km.setGovKeyWithAggKey(sigData, newGovKey);
    }

    function setGovKeyWithGovKey(address newGovKey) external {
        km.setGovKeyWithGovKey(newGovKey);
    }

    function setCommKeyWithAggKey(SigData calldata sigData, address newCommKey) external {
        km.setCommKeyWithAggKey(sigData, newCommKey);
    }

    function setCommKeyWithCommKey(address newCommKey) external {
        km.setCommKeyWithCommKey(newCommKey);
    }

    function govAction(bytes32 message) external {
        km.govAction(message);
    }
}
