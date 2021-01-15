pragma solidity ^0.7.0;


import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/IVault.sol";
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

    // Constants
    /// @dev The address used to indicate whether transfer should send ETH or a token
    address constant private _ETH_ADDR = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    address constant private _ZERO_ADDR = address(0);
    bytes32 constant private _NULL = "";


    struct KeyData {
        uint pubKeyX;
        uint8 pubKeyYParity;
        address nonceTimesGAddr;
    }

    event KeyChange(
        bool keyChangedIsAggKey,
        uint indexed sigKeyX,
        uint8 sigKeyYParity,
        address sigNonceTimesGAddr,
        uint indexed newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    );


    constructor(
        uint newAggKeyX,
        uint8 newAggKeyYParity,
        address newAggNonceTimesGAddr,
        uint newGovKeyX,
        uint8 newGovKeyYParity,
        address newGovNonceTimesGAddr
    ) {
        _aggregateKeyData = KeyData(newAggKeyX, newAggKeyYParity, newAggNonceTimesGAddr);
        _governanceKeyData = KeyData(newGovKeyX, newGovKeyYParity, newGovNonceTimesGAddr);
        _lastValidateTime = block.timestamp;
    }


    // -----Deposits/withdrawals-----


    /**
     * @notice  Transfers ETH or a token from this vault to a recipient
     * @param msgHash   The keccak256 hash over the msg, which is the calldata
     *                  for this function with empty msgHash and sig
     * @param sig       The schnorrSECP256K1 signature over the msgHash from _aggregateKeyData
     * @param tokenAddr The address of the token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei
     */
    function transfer(
        uint msgHash,
        uint sig,
        address tokenAddr,
        address payable recipient,
        uint amount
    ) external nzAddr(tokenAddr) nzAddr(recipient) nzUint(amount) validate(
        keccak256(abi.encodeWithSelector(
            this.transfer.selector,
            _NULL,
            _NULL,
            tokenAddr,
            recipient,
            amount
        )),
        msgHash,
        sig,
        _aggregateKeyData.pubKeyX,
        _aggregateKeyData.pubKeyYParity,
        _aggregateKeyData.nonceTimesGAddr
    ) {
        if (tokenAddr == _ETH_ADDR) {
            recipient.transfer(amount);
        } else {
            // It would be nice to wrap require around this line, but
            // some older tokens don't return a bool
            IERC20(tokenAddr).transfer(recipient, amount);
        }
    }

    /**
     * @notice  Retrieves ETH or a token from an address deterministically generated using
     *          create2 by creating a contract for that address, sending it to this vault, and
     *          then destroying
     * @param msgHash   The keccak256 hash over the msg, which is the calldata
     *                  for this function with empty msgHash and sig
     * @param sig       The schnorrSECP256K1 signature over the msgHash from _aggregateKeyData
     * @param swapID    The unique identifier for this swap
     * @param tokenAddr The address of the token to be transferred
     * @param amount    The amount to retrieve, in wei
     */
    function fetchDeposit(
        uint msgHash,
        uint sig,
        bytes32 swapID,
        address tokenAddr,
        uint amount
    ) external nzBytes32(swapID) nzAddr(tokenAddr) nzUint(amount) validate(
        keccak256(abi.encodeWithSelector(
            this.fetchDeposit.selector,
            _NULL,
            _NULL,
            swapID,
            tokenAddr,
            amount
        )),
        msgHash,
        sig,
        _aggregateKeyData.pubKeyX,
        _aggregateKeyData.pubKeyYParity,
        _aggregateKeyData.nonceTimesGAddr
    ) {
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
     * @notice  Set a new _aggregateKeyData. Requires a signature from the current _aggregateKeyData
     * @param msgHash   The keccak256 hash over the msg, which is the calldata
     *                  for this function with empty msgHash and sig
     * @param sig       The schnorrSECP256K1 signature over the msgHash from _aggregateKeyData
     * @param newKeyX   The x coordinate of the public key of the new _aggregateKeyData, as uint
     * @param newKeyYParity The parity of the y coordinate of the public key of the new
                            _aggregateKeyData. 0 if it's even, 1 if it's odd
     * @param newNonceTimesGAddr    The newNonceTimesGeneratorAddress of the new key
     */
    function setAggKeyByAggKey(
        uint msgHash,
        uint sig,
        uint newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    ) external nzUint(newKeyX) nzAddr(newNonceTimesGAddr) validate(
        keccak256(abi.encodeWithSelector(
            this.setAggKeyByAggKey.selector,
            _NULL,
            _NULL,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        )),
        msgHash,
        sig,
        _aggregateKeyData.pubKeyX,
        _aggregateKeyData.pubKeyYParity,
        _aggregateKeyData.nonceTimesGAddr
    ) {
        emit KeyChange(
            true,
            _aggregateKeyData.pubKeyX,
            _aggregateKeyData.pubKeyYParity,
            _aggregateKeyData.nonceTimesGAddr,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        );
        _aggregateKeyData = KeyData(newKeyX, newKeyYParity, newNonceTimesGAddr);
    }

    /**
     * @notice  Set a new _aggregateKeyData. Requires a signature from the current _governanceKeyData
     * @param msgHash   The keccak256 hash over the msg, which is the calldata
     *                  for this function with empty msgHash and sig
     * @param sig       The schnorrSECP256K1 signature over the msgHash from _governanceKeyData
     * @param newKeyX   The x coordinate of the public key of the new _aggregateKeyData, as uint
     * @param newKeyYParity The parity of the y coordinate of the public key of the new
                            _aggregateKeyData. 0 if it's even, 1 if it's odd
     * @param newNonceTimesGAddr    The newNonceTimesGeneratorAddress of the new key
     */
    function setAggKeyByGovKey(
        uint msgHash,
        uint sig,
        uint newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    ) external nzUint(newKeyX) nzAddr(newNonceTimesGAddr) validate(
        keccak256(abi.encodeWithSelector(
            this.setAggKeyByGovKey.selector,
            _NULL,
            _NULL,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        )),
        msgHash,
        sig,
        _governanceKeyData.pubKeyX,
        _governanceKeyData.pubKeyYParity,
        _governanceKeyData.nonceTimesGAddr
    ) {
        emit KeyChange(
            true,
            _aggregateKeyData.pubKeyX,
            _aggregateKeyData.pubKeyYParity,
            _aggregateKeyData.nonceTimesGAddr,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        );
        _aggregateKeyData = KeyData(newKeyX, newKeyYParity, newNonceTimesGAddr);
    }

    /**
     * @notice  Set a new _governanceKeyData. Requires a signature from the current _governanceKeyData
     * @param msgHash   The keccak256 hash over the msg, which is the calldata
     *                  for this function with empty msgHash and sig
     * @param sig       The schnorrSECP256K1 signature over the msgHash from _governanceKeyData
     * @param newKeyX   The x coordinate of the public key of the new _governanceKeyData, as uint
     * @param newKeyYParity The parity of the y coordinate of the public key of the new
                            _governanceKeyData. 0 if it's even, 1 if it's odd
     * @param newNonceTimesGAddr    The newNonceTimesGeneratorAddress of the new key
     */
    function setGovKeyByGovKey(
        uint msgHash,
        uint sig,
        uint newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    ) external nzUint(newKeyX) nzAddr(newNonceTimesGAddr) validate(
        keccak256(abi.encodeWithSelector(
            this.setGovKeyByGovKey.selector,
            _NULL,
            _NULL,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        )),
        msgHash,
        sig,
        _governanceKeyData.pubKeyX,
        _governanceKeyData.pubKeyYParity,
        _governanceKeyData.nonceTimesGAddr
    ) {
        emit KeyChange(
            false,
            _governanceKeyData.pubKeyX,
            _governanceKeyData.pubKeyYParity,
            _governanceKeyData.nonceTimesGAddr,
            newKeyX,
            newKeyYParity,
            newNonceTimesGAddr
        );
        _governanceKeyData = KeyData(newKeyX, newKeyYParity, newNonceTimesGAddr);
    }


    // -----Getters-----

    /**
     * @notice  Get all elements of the current _aggregateKeyData
     * @return  The x coordinate as a uint
     * @return  The y parity as a uint8. 0 if it's even, 1 if it's odd
     * @return  The nonceTimesGeneratorAddress
     */
    function getAggregateKeyData() external view returns (uint, uint8, address) {
        return (
            _aggregateKeyData.pubKeyX,
            _aggregateKeyData.pubKeyYParity,
            _aggregateKeyData.nonceTimesGAddr
        );
    }

    /**
     * @notice  Get all elements of the current _governanceKeyData
     * @return  The x coordinate as a uint
     * @return  The y parity as a uint8. 0 if it's even, 1 if it's odd
     * @return  The nonceTimesGeneratorAddress
     */
    function getGovernanceKeyData() external view returns (uint, uint8, address) {
        return (
            _governanceKeyData.pubKeyX,
            _governanceKeyData.pubKeyYParity,
            _governanceKeyData.nonceTimesGAddr
        );
    }

    /**
     * @notice  Get the last time that a function was called which
                requires a signature from _aggregateKeyData or _governanceKeyData
     * @return  The last time validate was called, in unix time
     */
    function getLastValidateTime() external view returns (uint) {
        return _lastValidateTime;
    }


    // -----Modifiers-----

    /// @dev Checks the validity of a signature and msgHash, then updates _lastValidateTime
    // It would be nice to split this up, but these checks need to be made atomicly always
    modifier validate(
        bytes32 contractMsgHash,
        uint msgHash,
        uint sig,
        uint pubKeyX,
        uint8 pubKeyYParity,
        address nonceTimesGAddr
    ) {
        require(msgHash == uint(contractMsgHash), "Vault: invalid msgHash");
        require(
            verifySignature(
                msgHash,
                sig,
                pubKeyX,
                pubKeyYParity,
                nonceTimesGAddr
            ),
            "Vault: Sig invalid"
        );
        _lastValidateTime = block.timestamp;
        _;
    }

    /// @dev Checks that a uint isn't nonzero/empty
    modifier nzUint(uint u) {
        require(u != 0, "Vault: uint input is empty");
        _;
    }

    /// @dev Checks that an address isn't nonzero/empty
    modifier nzAddr(address a) {
        require(a != _ZERO_ADDR, "Vault: address input is empty");
        _;
    }

    /// @dev Checks that a bytes32 isn't nonzero/empty
    modifier nzBytes32(bytes32 b) {
        require(b != _NULL, "Vault: bytes32 input is empty");
        _;
    }


    // -----Fallbacks-----

    /// @dev For receiving ETH when fetchDeposit is called
    receive() external payable {}
}