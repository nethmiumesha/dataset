// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CashBackManager_430284 {
    mapping(address => uint256) public cashBack;

    function sendRefund(address payable recipient) external {
        uint256 refund = cashBack[recipient];
        cashBack[recipient] = 0;
        // Flaw: .send() returns false on error but return value is unhandled
        recipient.send(refund);
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
