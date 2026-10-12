// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VaultController_644588 {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    function destroyEmergency() external {
        // Missing onlyOwner or access restriction
        selfdestruct(payable(msg.sender));
    }
}
