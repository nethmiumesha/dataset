// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VaultController_452344 {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    function destroyEmergency() external {
        // Missing onlyOwner or access restriction
        selfdestruct(payable(msg.sender));
    }
}
