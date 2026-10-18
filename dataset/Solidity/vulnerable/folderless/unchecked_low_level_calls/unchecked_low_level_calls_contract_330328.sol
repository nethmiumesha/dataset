// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRelay_330328 {
    function relayAction(address target, bytes calldata data) external {
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
