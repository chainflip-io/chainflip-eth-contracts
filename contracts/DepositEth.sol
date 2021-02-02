pragma solidity ^0.7.0;


contract DepositEth {

    constructor() {
        // This contract should only have been created if there's
        // already enough Eth here. This will also send any excess
        // that the user mistakenly sent
        selfdestruct(msg.sender);
    }

}