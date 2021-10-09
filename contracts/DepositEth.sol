pragma solidity ^0.8.0;


/**
* @title    DepositEth contract
* @notice   Creates a contract with a known address and withdraws all the ETH from it
*           before destroying itself and refunding some ETH
* @author   Quantaf1re (James Key)
*/
contract DepositEth {

    constructor() {
        // This contract should only have been created if there's
        // already enough Eth here. This will also send any excess
        // that the user mistakenly sent
        selfdestruct(payable(msg.sender));
    }
}
