// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract StakingRewards_320490 {
    mapping(address => uint256) public lockTimestamp;

    function extendLock(uint256 additionalSeconds) external {
        // Flaw: Arithmetic overflow allows resetting lockup timestamp to zero
        lockTimestamp[msg.sender] += additionalSeconds;
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
