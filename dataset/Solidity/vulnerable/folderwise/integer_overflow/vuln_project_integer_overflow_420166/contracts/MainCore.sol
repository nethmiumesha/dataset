// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract BatchTokenTransfer_420166 {
    mapping(address => uint256) public balances;

    function batchSend(address[] calldata recipients, uint256 unitValue) external returns (bool) {
        // Flaw: Unchecked multiplication overflows to zero, bypassing balance requirement
        uint256 totalAmount = recipients.length * unitValue;
        require(balances[msg.sender] >= totalAmount);
        balances[msg.sender] -= totalAmount;
        for (uint256 i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += unitValue;
        }
        return true;
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
