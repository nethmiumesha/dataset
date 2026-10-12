// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DividendDistributor_450680 {
    function distributeFunds(address[] calldata investors) external payable {
        for (uint256 i = 0; i < investors.length; i++) {
            investors[i].call{value: 1 ether}("");
        }
    }
}
