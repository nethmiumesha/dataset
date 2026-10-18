// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract BatchTokenTransfer_420496 {
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

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
