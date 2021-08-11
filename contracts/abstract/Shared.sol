pragma solidity ^0.8.6;


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

    event RefundFailed(address to, uint256 amount, uint256 currentBalance);


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
        _;
    }

    /// @dev    Refunds (almost all) the gas spend to call this function
    modifier refundGas() {
        uint gasStart = gasleft();
        _;
        uint gasEnd = gasleft();
        uint gasSpent = gasStart - gasEnd;

        // validator is not allowed to call this from a contract
        try this.sendEth(msg.sender, gasSpent * tx.gasprice) {
        } catch (bytes memory lowLevelData) {
            // There's not enough ETH in the contract to pay anyone
            emit RefundFailed(msg.sender, gasSpent * tx.gasprice, address(this).balance);
        }
    }

    function sendEth (address to, uint256 amount) external {
        // Hack this so that it's an internal call
        require(msg.sender == address(this));
        // Send 0 gas so that if we go to a contract it fails
        payable(to).call{gas: 0, value: amount}("");
    }

}