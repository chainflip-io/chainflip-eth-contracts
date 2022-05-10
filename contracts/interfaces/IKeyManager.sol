pragma solidity ^0.8.0;

import "./IShared.sol";

/**
 * @title    KeyManager interface
 * @notice   The interface for functions KeyManager implements
 * @author   Quantaf1re (James Key)
 */
interface IKeyManager is IShared {
    event AggKeySetByAggKey(Key oldKey, Key newKey);
    event AggKeySetByGovKey(Key oldKey, Key newKey);
    event GovKeySetByAggKey(address oldKey, address newKey);
    event GovKeySetByGovKey(address oldKey, address newKey);
    event CommKeySetByAggKey(address oldKey, address newKey);
    event CommKeySetByCommKey(address oldKey, address newKey);
    event SignatureAccepted(SigData sigData, address signer);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function consumeKeyNonce(SigData memory sigData, bytes32 contractMsgHash) external;

    function setAggKeyWithAggKey(SigData memory sigData, Key memory newAggKey) external;

    function setAggKeyWithGovKey(Key memory newAggKey) external;

    function setGovKeyWithAggKey(SigData calldata sigData, address newGovKey) external;

    function setGovKeyWithGovKey(address newGovKey) external;

    function setCommKeyWithAggKey(SigData calldata sigData, address newCommKey) external;

    function setCommKeyWithCommKey(address newCommKey) external;

    function canConsumeKeyNonce(address addr) external view returns (bool);

    function canConsumeKeyNonceSet() external view returns (bool);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getAggregateKey() external view returns (Key memory);

    function getGovernanceKey() external view returns (address);

    function getCommunityKey() external view returns (address);

    function getLastValidateTime() external view returns (uint256);

    function getNumberWhitelistedAddresses() external view returns (uint256);

    function isNonceUsedByAggKey(uint256 nonce) external view returns (bool);
}
