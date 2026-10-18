// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract StakingPool_101028 {
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

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
