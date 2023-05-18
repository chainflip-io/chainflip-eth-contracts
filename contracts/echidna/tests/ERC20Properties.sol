pragma solidity ^0.8.0;
import "../../FLIP.sol";
import {ITokenMock} from "@crytic/properties/contracts/ERC20/external/util/ITokenMock.sol";
import {CryticERC20ExternalBasicProperties} from "@crytic/properties/contracts/ERC20/external/properties/ERC20ExternalBasicProperties.sol";
import {CryticERC20ExternalIncreaseAllowanceProperties} from "@crytic/properties/contracts/ERC20/external/properties/ERC20ExternalIncreaseAllowanceProperties.sol";
import {CryticERC20ExternalMintableProperties} from "@crytic/properties/contracts/ERC20/external/properties/ERC20ExternalMintableProperties.sol";
import {CryticERC20ExternalBurnableProperties} from "@crytic/properties/contracts/ERC20/external/properties/ERC20ExternalBurnableProperties.sol";
import {PropertiesConstants} from "@crytic/properties/contracts/util/PropertiesConstants.sol";


contract CryticERC20ExternalHarness is CryticERC20ExternalBasicProperties,
                                       CryticERC20ExternalIncreaseAllowanceProperties,
                                       CryticERC20ExternalMintableProperties, 
                                       CryticERC20ExternalBurnableProperties {
    constructor() {
        // Deploy ERC20
        token = ITokenMock(address(new CryticTokenMock()));
    }
}

contract CryticTokenMock is FLIP, PropertiesConstants {

    bool public isMintableOrBurnable;
    uint256 public initialSupply;
    constructor () FLIP(
            10**30,
            1,
            10**18,
            address(0x10000),
            address(0x20000),
            address(0x10000)
        ) {
        _mint(USER1, INITIAL_BALANCE);
        _mint(USER2, INITIAL_BALANCE);
        _mint(USER3, INITIAL_BALANCE);
        _mint(msg.sender, INITIAL_BALANCE);

        initialSupply = totalSupply();
        isMintableOrBurnable = true;
    }
}