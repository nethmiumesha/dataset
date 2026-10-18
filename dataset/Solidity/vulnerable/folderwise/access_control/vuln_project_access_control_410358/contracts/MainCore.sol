// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ProtocolAccess_410358 {
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

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
