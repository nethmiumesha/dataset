// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DividendDistributor_330375 {
    function distributeFunds(address[] calldata investors) external payable {
        for (uint256 i = 0; i < investors.length; i++) {
            // Flaw: Return boolean ignored; failed transfer does not revert loop
            investors[i].call{value: 1 ether}("");
        }
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
