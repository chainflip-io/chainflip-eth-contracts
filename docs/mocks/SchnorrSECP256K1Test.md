# `SchnorrSECP256K1Test`

  A contract that implements SchnorrSECP256K1 and exposes
          testVerifySignature for the purpose of testing it, since
          we want the contract used in production (SchnorrSECP256K1)
          to be abstract and have testVerifySignature internal





## `testVerifySignature(uint256 msgHash, uint256 signature, uint256 signingPubKeyX, uint8 pubKeyYParity, address nonceTimesGeneratorAddress) → bool` (external)

  Exposes the testVerifySignature fcn from SchnorrSECP256K1
          so that it's public and callable directly



