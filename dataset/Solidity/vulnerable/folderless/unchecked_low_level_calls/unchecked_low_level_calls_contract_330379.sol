// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CashBackManager_330379 {
    mapping(address => uint256) public cashBack;

    function sendRefund(address payable recipient) external {
        uint256 refund = cashBack[recipient];
        cashBack[recipient] = 0;
        // Flaw: .send() returns false on error but return value is unhandled
        recipient.send(refund);
    }
}
