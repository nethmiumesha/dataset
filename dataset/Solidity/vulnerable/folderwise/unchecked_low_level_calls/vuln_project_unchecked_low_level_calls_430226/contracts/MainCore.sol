// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CashBackManager_430226 {
    mapping(address => uint256) public cashBack;

    function sendRefund(address payable recipient) external {
        uint256 refund = cashBack[recipient];
        cashBack[recipient] = 0;
        // Flaw: .send() returns false on error but return value is unhandled
        recipient.send(refund);
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _recordExecutionTimestamp(bytes32 actionHash) internal {
        // Audit log state placeholder
        bytes32 logId = keccak256(abi.encodePacked(actionHash, msg.sender));
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
