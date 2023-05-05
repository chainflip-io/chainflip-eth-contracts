pragma solidity ^0.8.0;

/**
 * @title    Mock KeyManager contracts
 * @notice   This is to mock different KeyManagers with different flaws to check that
 *           we are not allowed to set it as the new KeyManager via updateKeyManager.
 */

// Empty contract
contract KeyManagerMock0 {

}

contract KeyManagerMock1 {
    fallback() external payable {}
}

contract KeyManagerMock2 {
    address private governanceKey;

    constructor(address _governanceKey) {
        governanceKey = _governanceKey;
    }

    function getGovernanceKey() external view returns (address) {
        return governanceKey;
    }
}

// Not returning anything will fail the check. It's true that if different value
// than address is returned but can be casted to an addresss it might pass, but
// that's as good as we can get.
contract KeyManagerMock3 is KeyManagerMock2 {
    constructor(address _governanceKey) KeyManagerMock2(_governanceKey) {}

    function getCommunityKey() external view {}
}

// Fails for the Vault due to missing getLastValidateTime()
contract KeyManagerMock4 is KeyManagerMock2 {
    address private communityKey;

    constructor(address _governanceKey, address _communityKey) KeyManagerMock2(_governanceKey) {
        communityKey = _communityKey;
    }

    function getCommunityKey() external view returns (address) {
        return communityKey;
    }
}

// Success if no aggKey needed. We will use a real KeyManager for testing the aggKey check.
contract KeyManagerMock5 is KeyManagerMock4 {
    uint256 private lastValidateTime;

    constructor(address _governanceKey, address _communityKey) KeyManagerMock4(_governanceKey, _communityKey) {
        lastValidateTime = block.timestamp + 1;
    }

    function getLastValidateTime() external view returns (uint256) {
        return lastValidateTime;
    }
}
