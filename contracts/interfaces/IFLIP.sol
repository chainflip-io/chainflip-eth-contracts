pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title    FLIP interface for the FLIP utility token
 */
interface IFLIP is IERC20 {
    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function mint(address receiver, uint amount) external;

    function burn(address owner, uint amount) external;

    function updateIssuer(address newOwner) external;
}
