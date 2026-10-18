// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VaultController_410140 {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    function destroyEmergency() external {
        // Flaw: Missing onlyOwner guard enables arbitrary contract destruction
        selfdestruct(payable(msg.sender));
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
