pragma solidity ^0.7.0;


import "../interfaces/IERC20.sol";


contract Deposit {
    event DepositFetched(address indexed depositAddr, address indexed tokenAddr, uint indexed amount);

    constructor(address tokenAddr, uint amount) {
        emit DepositFetched(address(this), tokenAddr, amount);
        // Normally using address(0) is a nono because people
        // can accidentally call it, but since this will only
        // be called by a contract with address(0) under the 
        // right condition, it reduces the bytecode by allowing
        // us to not store 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE
        if (tokenAddr == address(0)) {
            // Technically this line shouldn't be necessary if 
            // this contract is only created after the user has 
            // already deposited enough Ether since the selfdestruct
            // will transfer all of it
            msg.sender.transfer(amount);
        } else {
            IERC20(tokenAddr).transfer(msg.sender, amount);
        }

        // Incase there's any leftover Ether because the user
        // sent too much
        selfdestruct(msg.sender);
    }

}