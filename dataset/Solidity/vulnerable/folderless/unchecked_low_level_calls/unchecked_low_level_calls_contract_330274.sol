// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CashBackManager_330274 {
    mapping(address => uint256) public cashBack;

    function sendRefund(address payable recipient) external {
        uint256 refund = cashBack[recipient];
        cashBack[recipient] = 0;
        // Flaw: .send() returns false on error but return value is unhandled
        recipient.send(refund);
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function _recordExecutionTimestamp(bytes32 actionHash) internal {
        // Audit log state placeholder
        bytes32 logId = keccak256(abi.encodePacked(actionHash, msg.sender));
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }
}
