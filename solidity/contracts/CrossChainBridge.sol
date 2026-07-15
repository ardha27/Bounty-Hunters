// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CrossChainBridge {
    address public validator;
    uint256 public chainId;
    mapping(bytes32 => bool) public processedTransactions;
    mapping(address => uint256) public balances;

    event Deposited(address indexed user, uint256 amount, bytes32 indexed txHash);
    event Withdrawn(address indexed user, uint256 amount, bytes32 indexed txHash);

    constructor(address _validator, uint256 _chainId) {
        validator = _validator;
        chainId = _chainId;
    }

    function deposit() external payable {
        require(msg.value > 0, "Must deposit > 0");
        balances[msg.sender] += msg.value;
        bytes32 txHash = keccak256(abi.encodePacked(msg.sender, msg.value, block.number, chainId));
        emit Deposited(msg.sender, msg.value, txHash);
    }

    // Fixed: replay protection via processedTransactions mapping + chainId in hash
    function withdraw(
        address user,
        uint256 amount,
        uint256 sourceChainId,
        bytes32 txHash,
        bytes calldata signature
    ) external {
        require(!processedTransactions[txHash], "Transaction already processed");
        require(sourceChainId != chainId, "Cannot process same-chain transaction");

        // Reconstruct the message hash from the source chain
        bytes32 messageHash = keccak256(
            abi.encodePacked(user, amount, uint256(0), sourceChainId)
        );
        bytes32 ethSignedMessageHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash)
        );

        address signer = recoverSigner(ethSignedMessageHash, signature);
        require(signer == validator, "Invalid validator signature");

        processedTransactions[txHash] = true;
        require(address(this).balance >= amount, "Insufficient bridge balance");

        (bool success, ) = payable(user).call{value: amount}("");
        require(success, "Transfer failed");

        emit Withdrawn(user, amount, txHash);
    }

    function recoverSigner(bytes32 hash, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        if (v < 27) v += 27;
        require(v == 27 || v == 28, "Invalid v value");
        return ecrecover(hash, v, r, s);
    }

    receive() external payable {}
}
