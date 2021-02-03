pragma solidity ^0.7.0;


import "../abstract/SchnorrSECP256K1.sol";



contract SchnorrSECP256K1Test is SchnorrSECP256K1 {

    function testVerifySignature(
        uint256 msgHash, 
        uint256 signature,
        uint256 signingPubKeyX,
        uint8 pubKeyYParity,
        address nonceTimesGeneratorAddress
    ) external pure returns (bool) {
        return verifySignature(
            msgHash,
            signature,
            signingPubKeyX,
            pubKeyYParity,
            nonceTimesGeneratorAddress
        );
    }

}