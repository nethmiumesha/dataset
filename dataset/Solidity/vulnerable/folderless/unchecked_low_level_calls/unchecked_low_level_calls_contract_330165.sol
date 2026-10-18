// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRelay_330165 {
    function relayAction(address target, bytes calldata data) external {
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }
}
