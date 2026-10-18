// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract BatchTokenTransfer_320316 {
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

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
