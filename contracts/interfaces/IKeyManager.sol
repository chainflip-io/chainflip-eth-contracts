// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./IShared.sol";

/**
 * @title    KeyManager interface
 * @notice   The interface for functions KeyManager implements
 */
interface IKeyManager is IShared {
    event AggKeySetByAggKey(Key oldAggKey, Key newAggKey);
    event AggKeySetByGovKey(Key oldAggKey, Key newAggKey);
    event GovKeySetByAggKey(address oldGovKey, address newGovKey);
    event GovKeySetByGovKey(address oldGovKey, address newGovKey);
    event CommKeySetByAggKey(address oldCommKey, address newCommKey);
    event CommKeySetByCommKey(address oldCommKey, address newCommKey);
    event SignatureAccepted(SigData sigData, address signer);
    event GovernanceAction(bytes32 message);

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

    function govAction(bytes32 message) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getAggregateKey() external view returns (Key memory);

    function getGovernanceKey() external view returns (address);

    function getCommunityKey() external view returns (address);

    function isNonceUsedByAggKey(uint256 nonce) external view returns (bool);

    function getLastValidateTime() external view returns (uint256);
}
