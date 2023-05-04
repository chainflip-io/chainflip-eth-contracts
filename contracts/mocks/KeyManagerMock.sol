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

// This should fail because of the wrong return type
contract KeyManagerMock1 is IShared {
    function consumeKeyNonce(SigData calldata, bytes32) external pure returns (bytes4) {
        return this.consumeKeyNonce.selector;
    }
}

// Fails due to missing supportsConsumeKeyNonce()
contract KeyManagerMock2 is IShared {
    function consumeKeyNonce(SigData calldata, bytes32) external pure {
        revert("Mock revert reason");
    }
}

// Check that reverting with an error has the same outcome as with a revert("")
contract KeyManagerMock3 is IShared {
    error DummyError();

    function consumeKeyNonce(SigData calldata, bytes32) external pure {
        revert DummyError();
    }
}

// Check that reverting with no data is problematic as it will fail the returndata.length > 0
// instead of failing due to missing getCommunityKey(). Then we can't tell if it has failed
// because the function doesn't exist or because it reverted with no data.
contract KeyManagerMock4 is IShared {
    function consumeKeyNonce(SigData calldata, bytes32) external pure {
        revert();
    }
}

// Fails due to missing getCommunityKey()
contract KeyManagerMock5 is KeyManagerMock2 {
    function getGovernanceKey() external view returns (address) {
        return address(this);
    }
}

// Fails due to having wrong return type
contract KeyManagerMock6 is KeyManagerMock5 {
    // Missing return value
    function getCommunityKey() external view {}
}

contract KeyManagerMock7 {
    fallback() external payable {}
}

// Fails for the Vault due to missing getLastValidateTime()
contract KeyManagerMock8 is KeyManagerMock5 {
    function getCommunityKey() external view returns (address) {
        return address(this);
    }
}

// Success
contract KeyManagerMock9 is KeyManagerMock8 {
    function getLastValidateTime() external view returns (uint256) {
        return block.timestamp;
    }
}

// "Problematic" - consumeKeyNonce() is not implemented but it doesn't
// fail. However, we have avoided the catastrophic error of having the
// funds stuck.
contract KeyManagerMock10 is IShared {
    function getGovernanceKey() external view returns (address) {
        // return address(this);
        return 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;
    }

    function getCommunityKey() external view returns (address) {
        // return address(this);
        return 0x976EA74026E726554dB657fA54763abd0C3a0aa9;
    }

    function getLastValidateTime() external view returns (uint256) {
        // return block.timestamp;
        return 0;
    }
}
