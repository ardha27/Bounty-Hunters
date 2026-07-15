// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MultiSigWallet {
    address[] public owners;
    uint256 public required;
    uint256 public transactionCount;
    uint256 private _reentrancyLock;

    struct Transaction {
        address to;
        uint256 value;
        bytes data;
        bool executed;
        uint256 confirmedAtBlock; // block-level snapshot for front-run protection
    }

    mapping(uint256 => Transaction) public transactions;
    mapping(uint256 => mapping(address => bool)) public confirmations;
    mapping(address => bool) public isOwner;

    event Submitted(uint256 indexed txId);
    event Confirmed(uint256 indexed txId, address indexed owner);
    event Executed(uint256 indexed txId);
    event Revoked(uint256 indexed txId, address indexed owner);

    modifier onlyOwner() {
        require(isOwner[msg.sender], "Not owner");
        _;
    }

    modifier nonReentrant() {
        require(_reentrancyLock == 0, "Reentrant call");
        _reentrancyLock = 1;
        _;
        _reentrancyLock = 0;
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
        require(to != address(0), "Zero address target");
        uint256 txId = transactionCount++;
        transactions[txId] = Transaction({
            to: to,
            value: value,
            data: data,
            executed: false,
            confirmedAtBlock: 0
        });
        emit Submitted(txId);
        return txId;
    }

    function confirmTransaction(uint256 txId) external onlyOwner {
        require(!transactions[txId].executed, "Already executed");
        require(!confirmations[txId][msg.sender], "Already confirmed");
        confirmations[txId][msg.sender] = true;
        emit Confirmed(txId, msg.sender);
    }

    function revokeConfirmation(uint256 txId) external onlyOwner {
        require(!transactions[txId].executed, "Already executed");
        require(confirmations[txId][msg.sender], "Not confirmed");
        confirmations[txId][msg.sender] = false;
        emit Revoked(txId, msg.sender);
    }

    function getConfirmationCount(uint256 txId) public view returns (uint256 count) {
        for (uint256 i = 0; i < owners.length; i++) {
            if (confirmations[txId][owners[i]]) count++;
        }
    }

    function isConfirmedAtBlock(uint256 txId, uint256 blockNumber) public view returns (bool) {
        uint256 count;
        address[] memory _owners = owners;
        for (uint256 i = 0; i < _owners.length; i++) {
            if (confirmations[txId][_owners[i]]) count++;
        }
        return count >= required
            && transactions[txId].confirmedAtBlock > 0
            && transactions[txId].confirmedAtBlock <= blockNumber;
    }

    function executeTransaction(uint256 txId) external onlyOwner nonReentrant {
        Transaction storage txn = transactions[txId];
        require(!txn.executed, "Already executed");
        require(getConfirmationCount(txId) >= required, "Not enough confirmations");

        // Snapshot confirmation at current block before execution
        txn.confirmedAtBlock = block.number;
        txn.executed = true;

        // Use local copies to prevent read-after-write issues in callback
        address to = txn.to;
        uint256 value = txn.value;
        bytes memory data = txn.data;

        (bool success, ) = to.call{value: value}(data);
        require(success, "Execution failed");

        emit Executed(txId);
    }

    receive() external payable {}

    // ponytail: gas cost may exceed 100k for complex data payloads.
    // add gas cap or delegatecall pattern when multi-sig usage grows.
}
