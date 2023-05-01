pragma solidity ^0.8.0;

import "../abstract/Shared.sol";

/**
 * @title    Mock KeyManager contracts
 * @notice   This is to mock different KeyManagers with different flaws to check that
 *           we are not allowed to set it as the new KeyManager via updateKeyManager.
 */

// Missing
contract KeyManagerMock0 {

}

contract KeyManagerMock1 is IShared {
    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) external {}
}

contract KeyManagerMock2 is KeyManagerMock1 {
    // Wrong selector
    function onKeyManagerUpdated() public pure returns (bytes4) {
        return this.onKeyManagerUpdated.selector;
    }
}

contract KeyManagerMock3 is KeyManagerMock1 {
    function onKeyManagerUpdated() public pure returns (bytes4) {
        return this.consumeKeyNonce.selector;
    }
}

contract KeyManagerMock4 is KeyManagerMock3 {
    function getGovernanceKey() external view returns (address) {
        return address(this);
    }
}

contract KeyManagerMock5 is KeyManagerMock4 {
    // Missing return value
    function getCommunityKey() external view {}
}

contract KeyManagerMock6 is KeyManagerMock4 {
    function getCommunityKey() external view returns (address) {
        return address(this);
    }
}

contract KeyManagerMock7 is KeyManagerMock6 {
    function getLastValidateTime() external view returns (uint256) {
        return block.timestamp;
    }
}
