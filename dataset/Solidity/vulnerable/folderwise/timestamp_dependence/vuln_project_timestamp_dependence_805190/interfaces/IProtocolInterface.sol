// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IProtocolInterface_805190 {
    function executeAction(address account, uint256 amount) external returns (bool);
    function getBalance(address target) external view returns (uint256);
}
