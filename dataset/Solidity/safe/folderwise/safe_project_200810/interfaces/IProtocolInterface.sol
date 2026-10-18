// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IProtocolInterface_200810 {
    function executeAction(address account, uint256 amount) external returns (bool);
    function getBalance(address target) external view returns (uint256);
}
