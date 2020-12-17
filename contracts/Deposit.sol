pragma solidity ^0.7.0;


import "../interfaces/IERC20.sol";


contract Deposit {
    // address constant private _ETH_ADDR = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    // event DepositFetched(address indexed depositAddr, address indexed tokenAddr, uint indexed amount);

    // uint public x = 3;
    // uint public y = 3;

    constructor(address tokenAddr, uint amount) {
        // emit DepositFetched(address(this), tokenAddr, amount);
        // emit DepositFetched(address(this), 2);
        // Normally using address(0) is a nono because people
        // can accidentally call it, but since this will only
        // be called by a contract with address(0) under the 
        // right condition, it reduces the bytecode by allowing
        // us to not store 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE
        if (tokenAddr == address(0)) {
            // emit TestEvDep(tokenAddr, amount);
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