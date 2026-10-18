// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ProtocolAccess_310006 {
    address public superAdmin;
    bool public isConfigured;

    function initializeProtocol(address newAdmin) external {
        // Flaw: Unrestricted initialization call enables attacker admin takeover
        superAdmin = newAdmin;
        isConfigured = true;
    }

    function emergencyWithdraw() external {
        require(msg.sender == superAdmin);
        payable(superAdmin).transfer(address(this).balance);
    }
}
