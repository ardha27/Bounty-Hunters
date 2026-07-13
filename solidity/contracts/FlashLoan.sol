// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IFlashLoanReceiver {
    function onFlashLoan(address token, uint256 amount, uint256 fee, bytes calldata data) external;
}

contract FlashLoan {
    IERC20 public loanToken;
    uint256 public feeBPS; // fee in basis points
    uint256 public totalFees;
    address public owner;
    bool public paused;

    // Internal accounting to prevent rebasing token manipulation
    uint256 public poolBalance;

    uint256 public constant MAX_LOAN_BPS = 5000; // 50% max loan

    event FlashLoanExecuted(address indexed borrower, uint256 amount, uint256 fee);
    event Paused(address indexed owner);
    event Unpaused(address indexed owner);
    event Deposited(address indexed depositor, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _loanToken, uint256 _feeBPS) {
        require(_feeBPS <= 10000, "Invalid fee BPS");
        loanToken = IERC20(_loanToken);
        feeBPS = _feeBPS;
        owner = msg.sender;
    }

    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender);
    }

    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }

    function flashLoan(uint256 amount, bytes calldata data) external {
        require(!paused, "Paused");
        require(amount > 0, "Amount must be > 0");

        // Max loan cap: 50% of pool balance to prevent drainage
        require(amount <= poolBalance * MAX_LOAN_BPS / 10000, "Loan exceeds max");

        // Minimum fee of 1 token to prevent zero-fee loans
        uint256 fee = amount * feeBPS / 10000;
        if (fee == 0) {
            fee = 1;
        }

        uint256 balanceBefore = poolBalance;
        require(balanceBefore >= amount, "Insufficient pool balance");

        // Transfer from internal pool balance
        poolBalance -= amount;
        loanToken.transfer(msg.sender, amount);

        IFlashLoanReceiver(msg.sender).onFlashLoan(address(loanToken), amount, fee, data);

        // Repayment: use token balance delta to support rebasing tokens too
        // But enforce at minimum the internal accounting amount
        uint256 currentBalance = loanToken.balanceOf(address(this));
        require(currentBalance >= balanceBefore + fee, "Loan not repaid");

        // Keep internal accounting deterministic; surplus donations/rebases require explicit deposit/sync logic.
        poolBalance = balanceBefore + fee;
        totalFees += fee;
        emit FlashLoanExecuted(msg.sender, amount, fee);
    }

    function depositToPool(uint256 amount) external {
        loanToken.transferFrom(msg.sender, address(this), amount);
        poolBalance += amount;
        emit Deposited(msg.sender, amount);
    }

    function withdrawFees() external onlyOwner {
        uint256 fees = totalFees;
        totalFees = 0;
        poolBalance -= fees;
        loanToken.transfer(owner, fees);
    }

    function getPoolBalance() external view returns (uint256) {
        return poolBalance;
    }
}
