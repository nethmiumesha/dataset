// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VaultController_410163 {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    function destroyEmergency() external {
        // Flaw: Missing onlyOwner guard enables arbitrary contract destruction
        selfdestruct(payable(msg.sender));
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
