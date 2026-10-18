// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VaultController_310379 {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    function destroyEmergency() external {
        // Flaw: Missing onlyOwner guard enables arbitrary contract destruction
        selfdestruct(payable(msg.sender));
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }
}
