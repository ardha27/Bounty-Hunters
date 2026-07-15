// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IFlashLoanReceiver {
    function executeOperation(address token, uint256 amount, uint256 fee, bytes calldata params) external returns (bool);
}

contract FlashLoan {
    mapping(address => uint256) public poolBalances;
    uint256 public flashLoanFee = 9; // 0.09% in basis points
    uint256 public constant MIN_FEE_BPS = 1; // minimum 0.01% fee
    address public owner;

    event FlashLoanExecuted(address indexed borrower, address token, uint256 amount, uint256 feePaid);

    constructor() {
        owner = msg.sender;
    }

    function deposit(address token, uint256 amount) external {
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        poolBalances[token] += amount;
    }

    function withdraw(address token, uint256 amount) external {
        require(msg.sender == owner, "Only owner");
        require(poolBalances[token] >= amount, "Insufficient balance");
        poolBalances[token] -= amount;
        IERC20(token).transfer(owner, amount);
    }

    function flashLoan(address token, uint256 amount, address receiver, bytes calldata params) external {
        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        require(balanceBefore >= amount, "Insufficient pool balance");

        // Enforce minimum fee to prevent zero-fee flash loans
        uint256 fee = amount * flashLoanFee / 10000;
        if (fee == 0) {
            fee = amount * MIN_FEE_BPS / 10000;
        }
        uint256 amountPlusFee = amount + fee;
        require(amountPlusFee > amount, "Fee overflow");

        IERC20(token).transfer(receiver, amount);

        require(
            IFlashLoanReceiver(receiver).executeOperation(token, amount, fee, params),
            "Flash loan failed"
        );

        uint256 balanceAfter = IERC20(token).balanceOf(address(this));
        require(balanceAfter >= balanceBefore + fee, "Flash loan not repaid with fee");

        emit FlashLoanExecuted(msg.sender, token, amount, fee);
    }

    receive() external payable {}
}
