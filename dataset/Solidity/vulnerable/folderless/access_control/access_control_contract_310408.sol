// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VaultController_310408 {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    function destroyEmergency() external {
        // Flaw: Missing onlyOwner guard enables arbitrary contract destruction
        selfdestruct(payable(msg.sender));
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
