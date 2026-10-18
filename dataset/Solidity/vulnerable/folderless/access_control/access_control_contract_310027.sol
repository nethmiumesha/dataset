// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ProtocolAccess_310027 {
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

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
