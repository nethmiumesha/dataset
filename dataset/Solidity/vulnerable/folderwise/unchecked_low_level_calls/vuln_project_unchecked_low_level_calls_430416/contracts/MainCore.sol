// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DividendDistributor_430416 {
    function distributeFunds(address[] calldata investors) external payable {
        for (uint256 i = 0; i < investors.length; i++) {
            // Flaw: Return boolean ignored; failed transfer does not revert loop
            investors[i].call{value: 1 ether}("");
        }
    }
}
