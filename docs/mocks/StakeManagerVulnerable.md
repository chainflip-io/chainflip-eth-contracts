# `StakeManagerVulnerable`



     This is purely for testing `noFish` which requires adding
          adding a fcn to send FLIP outside the contract without
          calling `claim`



## `constructor(contract IKeyManager keyManager, uint256 minStake, uint256 flipTotalSupply)` (public)

No description


## `testSetFLIP(contract FLIP flip)` (external)

 Can't set _FLIP in the constructor because it's made in the constructor
         of StakeManager and getFLIPAddress is external


- `flip`:      The address of the FLIP contract


## `testSendFLIP(address receiver, uint256 amount)` (external)

 Transfers FLIP out the contract


- `receiver`:  The address to send the FLIP to

- `amount`:    The amount of FLIP to send



