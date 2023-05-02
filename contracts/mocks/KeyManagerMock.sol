pragma solidity ^0.8.0;

import "../abstract/Shared.sol";

/**
 * @title    Mock KeyManager contracts
 * @notice   This is to mock different KeyManagers with different flaws to check that
 *           we are not allowed to set it as the new KeyManager via updateKeyManager.
 */

// Empty contract
contract KeyManagerMock0 {

}

// Fails due to missing supportsConsumeKeyNonce()
contract KeyManagerMock1 is IShared {
    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) external {}
}

// Fails due to wrong returned selector
contract KeyManagerMock2 is KeyManagerMock1 {
    function supportsConsumeKeyNonce() public pure returns (bytes4) {
        return this.supportsConsumeKeyNonce.selector;
    }
}

// Fails due to missing getGovernanceKey()
contract KeyManagerMock3 is KeyManagerMock1 {
    function supportsConsumeKeyNonce() public pure returns (bytes4) {
        return this.consumeKeyNonce.selector;
    }
}

// Fails due to missing getCommunityKey()
contract KeyManagerMock4 is KeyManagerMock3 {
    function getGovernanceKey() external view returns (address) {
        return address(this);
    }
}

// Fails due to having wrong return type
contract KeyManagerMock5 is KeyManagerMock4 {
    // Missing return value
    function getCommunityKey() external view {}
}

// Fails for the Vault due to missing getLastValidateTime()
contract KeyManagerMock6 is KeyManagerMock4 {
    function getCommunityKey() external view returns (address) {
        return address(this);
    }
}

// Success
contract KeyManagerMock7 is KeyManagerMock6 {
    function getLastValidateTime() external view returns (uint256) {
        return block.timestamp;
    }
}
