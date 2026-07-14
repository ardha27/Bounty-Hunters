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
    uint256 internal poolBalance; // Internal accounting to prevent rebasing token exploits

    event FlashLoanExecuted(address indexed borrower, uint256 amount, uint256 fee);
    event Paused(address indexed owner);
    event Unpaused(address indexed owner);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _loanToken, uint256 _feeBPS) {
        loanToken = IERC20(_loanToken);
        feeBPS = _feeBPS;
        owner = msg.sender;
    }

    function flashLoan(uint256 amount, bytes calldata data) external {
        require(!paused, "Paused");
        require(amount > 0, "Amount must be > 0");

        uint256 poolBal = getPoolBalance();
        require(poolBal >= amount, "Insufficient pool balance");

        // Prevent pool drainage: max 50% of pool balance
        require(amount <= poolBal / 2, "Loan exceeds 50% of pool");

        // Fee calculation with minimum of 1 token unit to prevent zero-fee flash loans
        uint256 fee = amount * feeBPS / 10000;
        if (fee < 1) {
            fee = 1;
        }

        uint256 snapshotBalance = poolBalance;

        loanToken.transfer(msg.sender, amount);
        poolBalance -= amount;

        IFlashLoanReceiver(msg.sender).onFlashLoan(address(loanToken), amount, fee, data);

        // Use internal accounting to prevent rebasing token manipulation
        poolBalance += amount + fee;

        // Verify actual token balance matches internal accounting
        uint256 actualBalance = loanToken.balanceOf(address(this));
        require(actualBalance >= poolBalance, "Loan not fully repaid");

        totalFees += fee;
        emit FlashLoanExecuted(msg.sender, amount, fee);
    }

    function depositToPool(uint256 amount) external {
        loanToken.transferFrom(msg.sender, address(this), amount);
        poolBalance += amount;
    }

    function withdrawFees() external onlyOwner {
        uint256 fees = totalFees;
        totalFees = 0;
        loanToken.transfer(owner, fees);
        poolBalance -= fees;
    }

    // Emergency pause/unpause
    function setPaused(bool _paused) external onlyOwner {
        paused = _paused;
        if (_paused) {
            emit Paused(owner);
        } else {
            emit Unpaused(owner);
        }
    }

    function getPoolBalance() public view returns (uint256) {
        return poolBalance;
    }
}
