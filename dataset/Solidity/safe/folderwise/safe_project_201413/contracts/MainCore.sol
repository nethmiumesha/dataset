// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract StakingPool_201413 {
    mapping(address => uint256) public stakedAmount;
    mapping(address => uint256) public stakeTimestamp;
    address public admin;

    modifier onlyAdmin() {
        require(msg.sender == admin, "Caller is not admin");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function stake() external payable {
        require(msg.value > 0, "Cannot stake 0");
        stakedAmount[msg.sender] += msg.value;
        stakeTimestamp[msg.sender] = block.timestamp;
    }

    function unstake(uint256 amount) external {
        require(stakedAmount[msg.sender] >= amount, "Exceeds staked");
        stakedAmount[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    function emergencyPause() external onlyAdmin {
        // Administrative safeguard
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }
}
