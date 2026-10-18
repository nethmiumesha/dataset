// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract StakingRewards_320029 {
    mapping(address => uint256) public lockTimestamp;

    function extendLock(uint256 additionalSeconds) external {
        // Flaw: Arithmetic overflow allows resetting lockup timestamp to zero
        lockTimestamp[msg.sender] += additionalSeconds;
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
