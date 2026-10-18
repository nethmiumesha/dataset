// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract StakingRewards_420464 {
    mapping(address => uint256) public lockTimestamp;

    function extendLock(uint256 additionalSeconds) external {
        // Flaw: Arithmetic overflow allows resetting lockup timestamp to zero
        lockTimestamp[msg.sender] += additionalSeconds;
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
