pragma solidity ^0.8.0;


import "../interfaces/IShared.sol";


/**
* @title    Shared contract
* @notice   Holds constants and modifiers that are used in multiple contracts
* @dev      It would be nice if this could be a library, but modifiers can't be exported :(
* @author   Quantaf1re (James Key)
*/
abstract contract Shared is IShared {
    /// @dev The address used to indicate whether transfer should send ETH or a token
    address constant internal _ETH_ADDR = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    address constant internal _ZERO_ADDR = address(0);
    bytes32 constant internal _NULL = "";
    uint constant internal _E_18 = 10**18;
    uint constant internal _MAX_BPS = 10000;


    /// @dev    Checks that a uint isn't nonzero/empty
    modifier nzUint(uint u) {
        require(u != 0, "Shared: uint input is empty");
        _;
    }

    /// @dev    Checks that an address isn't nonzero/empty
    modifier nzAddr(address a) {
        require(a != _ZERO_ADDR, "Shared: address input is empty");
        _;
    }

    /// @dev    Checks that a bytes32 isn't nonzero/empty
    modifier nzBytes32(bytes32 b) {
        require(b != _NULL, "Shared: bytes32 input is empty");
        _;
    }

    /// @dev    Checks that all of a Key's values are populated
    modifier nzKey(Key memory key) {
        require(key.pubKeyX != 0, "Shared: pubKeyX is empty");
        require(key.nonceTimesGAddr != _ZERO_ADDR, "Shared: nonceTimesGAddr is empty");
        _;
    }

}