// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IFlashLoanReceiver {
    function onFlashLoan(address token, uint256 amount, uint256 fee, bytes calldata data) external returns (bytes32);
}

contract FlashLoan {
    IERC20 public token;
    address public owner;
    uint256 public feeBPS;
    uint256 public totalFeesAccrued;
    bool public paused;

    // Internal accounting for rebasing token protection
    uint256 public poolBalance;

    event FlashLoanExecuted(address indexed borrower, uint256 amount, uint256 fee);
    event FeesWithdrawn(address indexed to, uint256 amount);
    event Paused();
    event Unpaused();
    event PoolBalanceSynced(uint256 oldBalance, uint256 newBalance);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "Flash loans paused");
        _;
    }

    constructor(address _token, uint256 _feeBPS) {
        require(_feeBPS <= 100, "Fee too high");
        token = IERC20(_token);
        owner = msg.sender;
        feeBPS = _feeBPS;
    }

    function deposit(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        poolBalance += amount;
    }

    function withdraw(uint256 amount) external onlyOwner {
        poolBalance -= amount;
        token.transfer(owner, amount);
    }

    function executeFlashLoan(
        address receiver,
        uint256 amount,
        bytes calldata data
    ) external whenNotPaused returns (bool) {
        require(amount > 0, "Amount must be > 0");
        require(amount <= poolBalance / 2, "Exceeds 50% pool cap");

        uint256 fee = amount * feeBPS / 10000;
        if (fee == 0) fee = 1; // minimum fee of 1 token unit

        uint256 balanceBefore = poolBalance;

        token.transfer(receiver, amount);

        bytes32 result = IFlashLoanReceiver(receiver).onFlashLoan(
            address(token),
            amount,
            fee,
            data
        );
        require(result == keccak256("FLASH_LOAN_SUCCESS"), "Callback failed");

        uint256 repayAmount = amount + fee;
        uint256 actualReceived = token.balanceOf(address(this));

        uint256 expectedBalance = balanceBefore - amount + repayAmount;
        require(actualReceived >= expectedBalance, "Repay insufficient");

        uint256 actualRepaid = actualReceived - (balanceBefore - amount);
        poolBalance = actualReceived;
        totalFeesAccrued += actualRepaid - amount;

        emit FlashLoanExecuted(receiver, amount, fee);
        return true;
    }

    function pause() external onlyOwner {
        paused = true;
        emit Paused();
    }

    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused();
    }

    function withdrawFees(address to) external onlyOwner {
        uint256 fees = totalFeesAccrued;
        require(fees > 0, "No fees");
        totalFeesAccrued = 0;
        poolBalance -= fees;
        token.transfer(to, fees);
        emit FeesWithdrawn(to, fees);
    }

    function syncPoolBalance() external {
        uint256 actual = token.balanceOf(address(this));
        emit PoolBalanceSynced(poolBalance, actual);
        poolBalance = actual;
    }
}
