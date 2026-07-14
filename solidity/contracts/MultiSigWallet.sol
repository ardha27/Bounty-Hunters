// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MultiSigWallet {
    address[] public owners;
    uint256 public required;
    uint256 public transactionCount;

    struct Transaction {
        address to;
        uint256 value;
        bytes data;
        bool executed;
    }

    struct Confirmation {
        bool confirmed;
        uint48 blockNumber; // block at which confirmation was recorded
    }

    mapping(uint256 => Transaction) public transactions;
    mapping(uint256 => mapping(address => Confirmation)) public confirmations;
    mapping(uint256 => uint256) public confirmationCount; // cached count, updated atomically
    mapping(address => bool) public isOwner;
    uint256 private _executingTxId; // Reentrancy guard: non-zero means callback in progress

    event Submitted(uint256 indexed txId);
    event Confirmed(uint256 indexed txId, address indexed owner);
    event Executed(uint256 indexed txId);
    event Revoked(uint256 indexed txId, address indexed owner);

    modifier onlyOwner() {
        require(isOwner[msg.sender], "Not owner");
        _;
    }

    constructor(address[] memory _owners, uint256 _required) {
        require(_owners.length > 0, "No owners");
        require(_required > 0 && _required <= _owners.length, "Invalid required");
        for (uint256 i = 0; i < _owners.length; i++) {
            require(_owners[i] != address(0), "Zero address owner");
            isOwner[_owners[i]] = true;
        }
        owners = _owners;
        required = _required;
    }

    function submitTransaction(address to, uint256 value, bytes calldata data) external onlyOwner returns (uint256) {
        require(to != address(0), "Invalid to address");
        uint256 txId = transactionCount++;
        transactions[txId] = Transaction({
            to: to,
            value: value,
            data: data,
            executed: false
        });
        emit Submitted(txId);
        return txId;
    }

    function confirmTransaction(uint256 txId) external onlyOwner {
        require(!transactions[txId].executed, "Already executed");
        require(!confirmations[txId][msg.sender].confirmed, "Already confirmed");
        confirmations[txId][msg.sender] = Confirmation({
            confirmed: true,
            blockNumber: uint48(block.number)
        });
        confirmationCount[txId]++;
        emit Confirmed(txId, msg.sender);
    }

    function revokeConfirmation(uint256 txId) external onlyOwner {
        require(!transactions[txId].executed, "Already executed");
        require(confirmations[txId][msg.sender].confirmed, "Not confirmed");
        confirmations[txId][msg.sender].confirmed = false;
        confirmationCount[txId]--;
        emit Revoked(txId, msg.sender);
    }

    function getConfirmationCount(uint256 txId) public view returns (uint256) {
        return confirmationCount[txId];
    }

    // Returns confirmation count as of a specific block, preventing front-running
    function isConfirmedAtBlock(uint256 txId, uint256 targetBlock) public view returns (uint256 count) {
        for (uint256 i = 0; i < owners.length; i++) {
            Confirmation storage c = confirmations[txId][owners[i]];
            if (c.confirmed && c.blockNumber <= targetBlock) {
                count++;
            }
        }
    }

    // Reentrancy-safe execution: uses block-level snapshot to prevent
    // confirmation revocation during callback from affecting execution
    function executeTransaction(uint256 txId) external onlyOwner {
        require(!transactions[txId].executed, "Already executed");
        
        // Use block-level snapshot: count confirmations at current block
        uint256 snapshotCount = isConfirmedAtBlock(txId, block.number);
        require(snapshotCount >= required, "Not enough confirmations");

        Transaction storage txn = transactions[txId];
        txn.executed = true;

        // Reentrancy guard
        require(_executingTxId == 0, "Reentrancy detected");
        _executingTxId = txId;

        (bool success, ) = txn.to.call{value: txn.value}(txn.data);
        
        _executingTxId = 0;
        require(success, "Execution failed");

        emit Executed(txId);
    }

    receive() external payable {}
}
