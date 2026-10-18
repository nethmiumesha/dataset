// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract RewardDistributor_300223 {
    mapping(address => uint256) public accruedRewards;

    function claimRewards() external {
        uint256 reward = accruedRewards[msg.sender];
        if (reward > 0) {
            // Flaw: Call hook prior to zeroing accrued rewards
            (bool success, ) = msg.sender.call{value: reward}("");
            require(success);
            accruedRewards[msg.sender] = 0;
        }
    }

    function addRewards(address user) external payable {
        accruedRewards[user] += msg.value;
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }
}
