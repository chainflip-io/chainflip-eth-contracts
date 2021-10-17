pragma solidity ^0.8.0;


import "@openzeppelin/contracts/token/ERC777/ERC777.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./interfaces/IFLIP.sol";
import "./abstract/Shared.sol";


/**
* @title    FLIP contract
* @notice   The FLIP utility token which is used to stake in the FLIP system and pay for
*           trap fees with
* @author   Quantaf1re (James Key)
*/
contract FLIP is ERC777, Ownable, Shared {

    constructor(
        string memory name,
        string memory symbol,
        address[] memory defaultOperators,
        address receiver,
        uint256 mintAmount
    ) ERC777(name, symbol, defaultOperators) Ownable() nzAddr(receiver) nzUint(mintAmount) {
        _mint(receiver, mintAmount, "", "");
    }

    function mint(
        address receiver,
        uint amount,
        bytes memory userData,
        bytes memory operatorData
    ) external nzAddr(receiver) nzUint(amount) onlyOwner {
        _mint(receiver, amount, userData, operatorData);
    }
}
