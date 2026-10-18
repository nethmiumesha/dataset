// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ProtocolAccess_310453 {
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

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
