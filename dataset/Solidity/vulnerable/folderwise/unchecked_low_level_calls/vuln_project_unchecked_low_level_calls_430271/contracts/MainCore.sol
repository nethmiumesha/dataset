// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRelay_430271 {
    function relayAction(address target, bytes calldata data) external {
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }
}
