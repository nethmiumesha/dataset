// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract StakingRewards_320478 {
    mapping(address => uint256) public lockTimestamp;

    function extendLock(uint256 additionalSeconds) external {
        // Flaw: Arithmetic overflow allows resetting lockup timestamp to zero
        lockTimestamp[msg.sender] += additionalSeconds;
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }
}
