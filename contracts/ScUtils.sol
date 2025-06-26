// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./abstract/Shared.sol";
import "./interfaces/IStateChainGateway.sol";

contract ScUtils is Shared {
    // We should probably still attribute the delegation/action to an address in the payload
    // to allow the swapAndDelegate, where the msg.sender will be the Vault. We emit the msg.sender
    // in case we ever need it.
    event DepositToScGatewayAndScCall(address sender, uint256 amount, bytes scCall);
    event DepositToVaultAndScCall(address sender, uint256 amount, address token, bytes scCall);
    event DepositAndScCall(address sender, uint256 amount, address token, address to, bytes scCall);
    event CallSc(address sender, bytes scCall);

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

    /// We could put a minimum of token/FLIP/ETH for each of these actions. However
    /// that would be very arbitrary. We would need to get the governance key to modify
    /// it. It seems simpler to just add checks on the engine for amounts, like we do
    /// for the minimum deposit. Especially given that this scCalls are arbitrary so
    /// putting a minimum for each might not even make sense.
    function depositToScGateway(uint256 amount, bytes calldata scCall) public {
        _depositFrom(amount, FLIP, SC_GATEWAY);
        emit DepositToScGatewayAndScCall(msg.sender, amount, scCall);
    }

    function depositToVault(uint256 amount, address token, bytes calldata scCall) public payable {
        _depositFrom(amount, token, CF_VAULT);
        emit DepositToVaultAndScCall(msg.sender, amount, token, scCall);
    }

    // In case in the future there is a need to deposit to an arbitrary address.
    function depositTo(uint256 amount, address token, address to, bytes calldata scCall) public payable {
        _depositFrom(amount, token, to);
        emit DepositAndScCall(msg.sender, amount, token, to, scCall);
    }

    // For other actions that don't require payment. For example to undelegate.
    // We rely on Ethereum to not be DoS'd, otherwise we choose to add a minimum
    // payment.
    function callSc(bytes calldata scCall) public {
        emit CallSc(msg.sender, scCall);
    }

    function _depositFrom(uint256 amount, address token, address to) private {
        if (token != _NATIVE_ADDR) {
            require(msg.value == 0, "ScUtils: value should be zero");

            // Assumption of set token allowance by the user
            IERC20(token).transferFrom(msg.sender, to, amount);
        } else {
            require(amount == msg.value, "ScUtils: value should match amount");

            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = to.call{value: msg.value}("");
            require(success);
        }
    }

    // Receive a call from Chainflip and execute a deposit and SC Call. This can be useful
    // to have a swap + delegation, swap + staking without having to add that logic into the SC.
    function cfReceive(
        uint32,
        bytes calldata,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable onlyCfVault {
        (address to, bytes memory data) = abi.decode(message, (address, bytes));

        // Using `address(this)` as a way to signal that it's `fundStateChainAccount`
        // so we don't need nested `abi.encode`.
        if (to == address(this)) {
            // Fund State Chain account
            require(token == FLIP, "ScUtils: token is not FLIP");
            require(IERC20(FLIP).approve(SC_GATEWAY, amount));
            IStateChainGateway(SC_GATEWAY).fundStateChainAccount(bytes32(data), amount);
        } else if (to == SC_GATEWAY) {
            // Deposit to ScGateway
            require(token == FLIP, "ScUtils: token is not FLIP");
            _deposit(amount, FLIP, SC_GATEWAY);
            emit DepositToScGatewayAndScCall(msg.sender, amount, data);
        } else if (to == CF_VAULT) {
            // Deposit to Vault
            _deposit(amount, token, CF_VAULT);
            emit DepositToVaultAndScCall(msg.sender, amount, token, data);
        } else {
            _deposit(amount, token, to);
            emit DepositAndScCall(msg.sender, amount, token, to, data);
        }
    }

    function _deposit(uint256 amount, address token, address to) private {
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
