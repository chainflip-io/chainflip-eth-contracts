pragma solidity ^0.7.0;


// import "../interfaces/IVault.sol";
import "../interfaces/IERC20.sol";
import "./SchnorrSECP256K1.sol";
import "./DepositEth.sol";
import "./DepositToken.sol";


/**
* @title    Vault contract
* @notice   The vault for holding ETH/tokens, the current
*           aggregate/governance keys for authorising withdrawals,
*           and deploying contracts for individual deposits
* @author   Quantaf1re (James Key)
*/
contract Vault is SchnorrSECP256K1 {

    /// @dev The aggregate key data used by ETH vault nodes to sign transfers
    KeyData private _aggregateKeyData;
    /// @dev The governance key data of the current governance quorum
    KeyData private _governanceKeyData;
    /// @dev The most recent time that the validate() modifier was called
    uint private _lastValidateTime;
    /// @dev The bytecode for the create2 deposit contract

    // Constants
    /// @dev The address used to indicate whether transfer should send ETH or a token
    address constant private _ETH_ADDR = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    bytes32 constant private _NULL = "";


    struct KeyData {
        bytes32 pubKeyX;
        uint8 pubKeyYParity;
        address nonceTimesGAddr;
    }

    event KeyChange(
        bool keyChangedIsAggKey,
        bytes32 indexed sigKeyX,
        uint8 sigKeyYParity,
        address sigNonceTimesGAddr,
        bytes32 indexed newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    );


    constructor(
        bytes32 newAggKeyX,
        uint8 newAggKeyYParity,
        address newAggNonceTimesGAddr,
        bytes32 newGovKeyX,
        uint8 newGovKeyYParity,
        address newGovNonceTimesGAddr
    ) {
        _aggregateKeyData = KeyData(newAggKeyX, newAggKeyYParity, newAggNonceTimesGAddr);
        _governanceKeyData = KeyData(newGovKeyX, newGovKeyYParity, newGovNonceTimesGAddr);
        _lastValidateTime = block.timestamp;
    }


    // -----Deposits/withdrawals-----

    function transfer(
        address tokenAddr,
        address payable recipient,
        uint amount,
        bytes32 msgHash,
        bytes32 sig
    ) external validate(
        _aggregateKeyData.pubKeyX,
        _aggregateKeyData.pubKeyYParity,
        _aggregateKeyData.nonceTimesGAddr,
        msgHash,
        keccak256(abi.encodeWithSelector(
            this.transfer.selector,
            tokenAddr,
            recipient,
            amount,
            _NULL,
            _NULL
        )),
        sig
    ) {
        require(tokenAddr != address(0), "Vault: invalid tokenAddr");
        require(recipient != address(0), "Vault: invalid recipient");
        require(amount != 0, "Vault: invalid amount");

        if (tokenAddr == _ETH_ADDR) {
            recipient.transfer(amount);
        } else {
            // It would be good to wrap require around this line, but
            // some older tokens don't return a bool
            IERC20(tokenAddr).transfer(recipient, amount);
        }
    }

    function fetchDeposit(
        bytes32 swapID,
        address tokenAddr,
        uint amount,
        bytes32 msgHash,
        bytes32 sig
    ) external validate(
        _aggregateKeyData.pubKeyX,
        _aggregateKeyData.pubKeyYParity,
        _aggregateKeyData.nonceTimesGAddr,
        msgHash,
        keccak256(abi.encodeWithSelector(
            this.fetchDeposit.selector,
            swapID,
            tokenAddr,
            amount,
            _NULL,
            _NULL
        )),
        sig
    ) {
        require(swapID != _NULL, "Vault: invalid swapID");
        require(tokenAddr != address(0), "Vault: invalid tokenAddr");
        require(amount != 0, "Vault: invalid amount");

        if (tokenAddr == _ETH_ADDR) {
            DepositEth d = new DepositEth{salt: swapID}();
        } else {
            DepositToken d = new DepositToken{salt: swapID}(
                tokenAddr,
                amount
            );
        }
    }


    // -----Setters-----

    /**
     * @notice  Updates the aggregate key
     * @param sig           The aggregated signature of vault nodes
     * @param msgHash       The hash of the calldata with an empty sig
     */
    function setAggKeyByAggKey(
        bytes32 newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr,
        bytes32 msgHash,
        bytes32 sig
    ) external validate(
        _aggregateKeyData.pubKeyX,
        _aggregateKeyData.pubKeyYParity,
        _aggregateKeyData.nonceTimesGAddr,
        msgHash,
        keccak256(abi.encodeWithSelector(
            this.setAggKeyByAggKey.selector,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr,
            _NULL,
            _NULL
        )),
        sig
    ) {
        require(newKeyX != _NULL, "Vault: invalid newKeyX");
        // Shortened the message to make it fit within 32 bytes...
        require(newNonceTimesGAddr != address(0), "Vault:invalid newNonceTimesGAddr");

        _aggregateKeyData = KeyData(newKeyX, newKeyYParity, newNonceTimesGAddr);
        emit KeyChange(
            true,
            _aggregateKeyData.pubKeyX,
            _aggregateKeyData.pubKeyYParity,
            _aggregateKeyData.nonceTimesGAddr,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        );
    }

    function setAggKeyByGovKey(
        bytes32 newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr,
        bytes32 msgHash,
        bytes32 sig
    ) external validate(
        _governanceKeyData.pubKeyX,
        _governanceKeyData.pubKeyYParity,
        _governanceKeyData.nonceTimesGAddr,
        msgHash,
        keccak256(abi.encodeWithSelector(
            this.setAggKeyByGovKey.selector,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr,
            _NULL,
            _NULL
        )),
        sig
    ) {
        require(newKeyX != _NULL, "Vault: invalid newKeyX");
        // Shortened the message to make it fit within 32 bytes...
        require(newNonceTimesGAddr != address(0), "Vault:invalid newNonceTimesGAddr");

        _aggregateKeyData = KeyData(newKeyX, newKeyYParity, newNonceTimesGAddr);
        emit KeyChange(
            true,
            _aggregateKeyData.pubKeyX,
            _aggregateKeyData.pubKeyYParity,
            _aggregateKeyData.nonceTimesGAddr,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        );
    }

    function setGovKeyByGovKey(
        bytes32 newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr,
        bytes32 msgHash,
        bytes32 sig
    ) external validate(
        _governanceKeyData.pubKeyX,
        _governanceKeyData.pubKeyYParity,
        _governanceKeyData.nonceTimesGAddr,
        msgHash,
        keccak256(abi.encodeWithSelector(
            this.setGovKeyByGovKey.selector,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr,
            _NULL,
            _NULL
        )),
        sig
    ) {
        require(newKeyX != _NULL, "Vault: invalid newKeyX");
        // Shortened the message to make it fit within 32 bytes...
        require(newNonceTimesGAddr != address(0), "Vault:invalid newNonceTimesGAddr");

        _governanceKeyData = KeyData(newKeyX, newKeyYParity, newNonceTimesGAddr);
        emit KeyChange(
            false,
            _governanceKeyData.pubKeyX,
            _governanceKeyData.pubKeyYParity,
            _governanceKeyData.nonceTimesGAddr,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        );
    }


    // -----Getters-----

    function getAggregateKeyData() external view returns (bytes32, uint8, address) {
        return (
            _aggregateKeyData.pubKeyX,
            _aggregateKeyData.pubKeyYParity,
            _aggregateKeyData.nonceTimesGAddr
        );
    }

    function getGovernanceKeyData() external view returns (bytes32, uint8, address) {
        return (
            _governanceKeyData.pubKeyX,
            _governanceKeyData.pubKeyYParity,
            _governanceKeyData.nonceTimesGAddr
        );
    }


    // -----Modifiers-----

    // It would be nice to split this up, but these checks need to be made atomicly always
    modifier validate(
        bytes32 pubKeyX,
        uint8 pubKeyYParity,
        address nonceTimesGAddr,
        bytes32 msgHash,
        bytes32 contractMsgHash,
        bytes32 sig
    ) {
        require(
            verifySignature(
                uint(pubKeyX),
                pubKeyYParity,
                nonceTimesGAddr,
                uint(msgHash),
                uint(sig)
            ),
            "Vault: Sig invalid"
        );
        require(msgHash == contractMsgHash, "Vault: invalid msgHash");
        _lastValidateTime = block.timestamp;
        _;
    }


    // -----Fallbacks-----

    receive() external payable {}
}