// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./abstract/Shared.sol";

contract ScUtils is Shared {
    // We should probably still attribute the delegation/action to an address in the payload
    // to allow the swapAndDelegate, where the msg.sender will be the Vault. We emit the msg.sender
    // in case we ever need it.
    event DepositToScGateway(address sender, uint256 amount, bytes data);
    event DepositToVault(address sender, uint256 amount, address token, bytes data);
    event DepositTo(address sender, uint256 amount, address token, address to, bytes data);
    event Action(address sender, bytes data);

    // solhint-disable-next-line var-name-mixedcase
    address public immutable FLIP;
    // solhint-disable-next-line var-name-mixedcase
    address public immutable SC_GATEWAY;
    // solhint-disable-next-line var-name-mixedcase
    address public immutable CF_VAULT;

    // solhint-disable-next-line var-name-mixedcase
    constructor(address _FLIP, address _SC_GATEWAY, address _CF_VAULT) {
        FLIP = _FLIP;
        SC_GATEWAY = _SC_GATEWAY;
        CF_VAULT = _CF_VAULT;
    }

    // TODO: We might want to consider putting all of these under the depositTo function
    // to make it simpler. However, this is nice so we don't have to check the "to"
    // address in the engine.
    function depositToScGateway(uint256 amount, bytes calldata data) public {
        _depositFromUser(amount, FLIP, SC_GATEWAY);
        emit DepositToScGateway(msg.sender, amount, data);
    }

    function depositToVault(uint256 amount, address token, bytes calldata data) public payable {
        _depositFromUser(amount, token, CF_VAULT);
        emit DepositToVault(msg.sender, amount, token, data);
    }

    // In case in the future there is a need to deposit to an arbitrary address.
    function depositTo(uint256 amount, address token, address to, bytes calldata data) public payable {
        _depositFromUser(amount, token, to);
        emit DepositTo(msg.sender, amount, token, to, data);
    }

    function _depositFromUser(uint256 amount, address token, address to) private {
        if (token != _NATIVE_ADDR) {
            require(msg.value == 0, "ScUtils: msg.value should be zero");

            // Assumption of set token allowance by the user
            IERC20(token).transferFrom(msg.sender, to, amount);
        } else {
            require(amount == msg.value, "ScUtils: msg.value should match amount");
            amount = msg.value;

            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = to.call{value: amount}("");
            require(success);
        }
    }

    // For other actions that don't require payment. For example to undelegate.
    // We rely on Ethereum to not be DoS'd, otherwise we can just choose to add
    // a minimum.
    function action(bytes calldata data) public {
        emit Action(msg.sender, data);
    }

    // CCM + delegate
    function cfReceive(
        uint32,
        bytes calldata,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable onlyCfVault {
        (address to, bytes memory data) = abi.decode(message, (uint256, bytes));

        // TODO: We could consider also unifying this to only the DepositTo, same
        // as for the deposit functions.
        if (to == SC_GATEWAY) {
            // Deposit to ScGateway
            _depositTo(amount, FLIP, SC_GATEWAY);
            emit DepositToScGateway(msg.sender, amount, data);
        } else if (to == CF_VAULT) {
            // Deposit to Vault
            _depositTo(amount, token, CF_VAULT);
            emit DepositToVault(msg.sender, amount, token, data);
        } else {
            _depositTo(amount, token, to);
            emit DepositTo(msg.sender, amount, token, to, data);
        }
    }

    function _depositTo(uint256 amount, address token, address to) private {
        if (token != _NATIVE_ADDR) {
            require(msg.value == 0, "ScUtils: value should be zero");
            IERC20(token).transfer(to, amount);
        } else {
            require(amount == msg.value, "ScUtils: value should match amount");
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = to.call{value: msg.value}("");
            require(success);
        }
    }

    /// @dev Check that the sender is the Chainflip's Vault.
    modifier onlyCfVault() {
        require(msg.sender == CF_VAULT, "ScUtils: caller not Chainflip Vault");
        _;
    }
}
