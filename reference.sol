function callContractWithToken(
    string memory destinationChain,
    string memory contractAddress,
    bytes memory payload,
    string memory symbol,
    uint256 amount
) external;


function send(
    uint16 _dstChainId,
    bytes calldata _remoteAndLocalAddresses,
    bytes calldata _payload,
    address payable _refundAddress,
    address _zroPaymentAddress,
    bytes calldata _adapterParams // custom functionality
) external payable;


function xcall(
    uint32 _destination, 
    address _to, 
    address _asset, 
    address _delegate, 
    uint256 _amount, 
    uint256 _slippage, 
    bytes _callData
)external payable returns (bytes32)

// Hyperlane => returns a leaf node
interface IOutbox {
    function dispatch(
        uint32 _destinationDomain,
        bytes32 _recipientAddress,
        bytes calldata _messageBody
    ) external returns (uint256);
}

/////////////////////////////////////////////////////////////////////////////////////////


function _executeWithToken(
    string memory sourceChain,
    string memory sourceAddress,
    bytes calldata payload,
    string memory tokenSymbol,
    uint256 amount
) internal virtual {}




function lzReceive(
    uint16 _srcChainId, 
    bytes calldata _srcAddress, 
    uint64 _nonce, 
    bytes calldata _payload
    ) external;

    


function xReceive(
    bytes32 _transferId,
    uint256 _amount,
    address _asset,
    address _originSender,
    uint32 _origin,
    bytes memory _callData
)


//THORCHAIN EGRESS => 
// Makes a call with egress native token ( It will only ever be given the base asset (eg ETH). ). If that fails, then it tries to send that
// via address.transfer.
function transferOutAndCall(address payable target, address finalToken, address to, uint256 amountOutMin, string memory memo) public payable nonReentrant {
        uint256 _safeAmount = msg.value;
        (bool success, ) = target.call{value:_safeAmount}(abi.encodeWithSignature("swapOut(address,address,uint256)", finalToken, to, amountOutMin));
        if (!success) {
            payable(address(to)).transfer(_safeAmount); // If can't swap, just send the recipient the ETH
        }
        emit TransferOutAndCall(msg.sender, target, address(0), _safeAmount, finalToken, to, amountOutMin, memo);
    }
    
/////////////////////////////////////////////////////////////////////////////////////////
//// ADD GAS

//AXELAR

function addNativeGas(
    bytes32 txHash,
    uint256 logIndex,
    address refundAddress
) external payable override;

function addGas(
    bytes32 txHash,
    uint256 logIndex,
    address gasToken,
    uint256 gasFeeAmount,
    address refundAddress
) external override;

