// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./abstract/Shared.sol";
import "./interfaces/IStateChainGateway.sol";
import "./interfaces/IScUtils.sol";

// TODO: Consider allowing for arrays to do multiple things in one TX. Just making the scCall an
// array is not good enough, as each action might have a different amount. However, if we batch
// it all we should probably just pull the whole amount in one for tokens. Also verify for ETH
// that msg.value matches the full amount. TBD but it might be quite useful in the future
// for new features that might require managing a position, which could be multiple actions.

// Emiting the signer (tx.origin) for the State Chain for flexibility so the State Chain
// has all the information to execute the call.
contract ScUtils is Shared, IScUtils {
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

    /**
     * @notice  Deposit an amount of FLIP to the State Chain Gateway contract and perform
     *          a call to the State Chain.
     * @dev     There is no minimum amount of FLIP required for the deposit. It would be
     *          arbitrary to hardcode one and updating it via governance key is unnecessary.
     *          It is simpler to just have a minimum on the engine, like for minimum deposit
     *          channel deposit amounts.
     * @param amount    Amount of FLIP to transfer to the State Chain Gateway contract.
     * @param scCall    Arbitrary State Chain call bytes
     */
    function depositToScGateway(uint256 amount, bytes calldata scCall) public override {
        _depositFrom(amount, FLIP, SC_GATEWAY);
        // solhint-disable-next-line avoid-tx-origin
        emit DepositToScGatewayAndScCall(msg.sender, tx.origin, amount, scCall);
    }

    /**
     * @notice  Deposit an amount of any token or ETH to the Vault contract and perform
     *          a call to the State Chain.
     * @param amount    Amount to transfer to the State Chain Gateway contract.
     * @param scCall    Arbitrary State Chain call bytes
     */
    function depositToVault(uint256 amount, address token, bytes calldata scCall) public payable override {
        _depositFrom(amount, token, CF_VAULT);
        // solhint-disable-next-line avoid-tx-origin
        emit DepositToVaultAndScCall(msg.sender, tx.origin, amount, token, scCall);
    }

    /**
     * @notice  Deposit an amount of any token or ETH to the an address and perform
     *          a call to the State Chain.
     * @dev     To be used in the future if new features are added.
     * @param amount    Amount to transfer to the State Chain Gateway contract.
     * @param scCall    Arbitrary State Chain call bytes
     */
    function depositTo(uint256 amount, address token, address to, bytes calldata scCall) public payable override {
        _depositFrom(amount, token, to);
        // solhint-disable-next-line avoid-tx-origin
        emit DepositAndScCall(msg.sender, tx.origin, amount, token, to, scCall);
    }

    /**
     * @notice  Perform a call to the State Chain.
     * @param scCall    Arbitrary State Chain call bytes
     */
    function callSc(bytes calldata scCall) public override {
        // solhint-disable-next-line avoid-tx-origin
        emit CallSc(msg.sender, tx.origin, scCall);
    }

    function _depositFrom(uint256 amount, address token, address to) private {
        if (token != _NATIVE_ADDR) {
            require(msg.value == 0, "ScUtils: value not zero");

            // Assumption of set token allowance by the user
            IERC20(token).transferFrom(msg.sender, to, amount);
        } else {
            require(amount == msg.value, "ScUtils: value missmatch");

            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = to.call{value: msg.value}("");
            require(success);
        }
    }

    /**
     * @notice  Receive a CCM swap from Chainflip and execute a deposit and SC Call.
     *          This can be useful to have a swap + delegation, swap + staking without
     *          having to add that logic into the SC.
     * @dev     Using address(0) when coming from a cross-chain swap as the tx.origin
     *          will be the Chainflip validator's key, which shouldn't be used.
     * @param srcChain      The source chain according to the Chainflip Protocol's nomenclature.
     * @param srcAddress    Bytes containing the source address on the source chain.
     * @param message       Message containing the SC Call and the destination address to deposit
     *                      the assets. This contract's address is used to signal that it
     *                      should be used to fund a State Chain account.
     * @param token         Address of the token received. _NATIVE_ADDR if it's native tokens.
     * @param amount        Amount of tokens received. This will match msg.value for native tokens.
     */
    function cfReceive(
        uint32,
        bytes calldata,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable override onlyCfVault {
        (address to, bytes memory data) = abi.decode(message, (address, bytes));

        // Using `address(this)` as a way to signal that it's `fundStateChainAccount`
        // so we don't need nested `abi.encode`.
        if (to == address(this)) {
            // Fund State Chain account
            require(token == FLIP, "ScUtils: token not FLIP");
            require(IERC20(FLIP).approve(SC_GATEWAY, amount));
            IStateChainGateway(SC_GATEWAY).fundStateChainAccount(bytes32(data), amount);
        } else if (to == SC_GATEWAY) {
            // Deposit to ScGateway
            require(token == FLIP, "ScUtils: token not FLIP");
            _deposit(amount, FLIP, SC_GATEWAY);
            emit DepositToScGatewayAndScCall(msg.sender, address(0), amount, data);
        } else if (to == CF_VAULT) {
            // Deposit to Vault
            _deposit(amount, token, CF_VAULT);
            emit DepositToVaultAndScCall(msg.sender, address(0), amount, token, data);
        } else {
            _deposit(amount, token, to);
            emit DepositAndScCall(msg.sender, address(0), amount, token, to, data);
        }
    }

    function _deposit(uint256 amount, address token, address to) private {
        if (token != _NATIVE_ADDR) {
            require(msg.value == 0, "ScUtils: value not zero");
            IERC20(token).transfer(to, amount);
        } else {
            require(amount == msg.value, "ScUtils: value missmatch");
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = to.call{value: msg.value}("");
            require(success);
        }
    }

    /// @dev Check that the sender is the Chainflip's Vault.
    modifier onlyCfVault() {
        require(msg.sender == CF_VAULT, "ScUtils: caller not Cf Vault");
        _;
    }
}
