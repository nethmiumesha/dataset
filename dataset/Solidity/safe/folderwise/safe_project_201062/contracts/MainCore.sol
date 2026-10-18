// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TreasuryGovernor_201062 {
    address public governor;
    uint256 public proposalCounter;

    event ProposalExecuted(uint256 indexed id);

    constructor() {
        governor = msg.sender;
    }

    function executeDisbursement(address recipient, uint256 amount) external {
        require(msg.sender == governor, "Unauthorized access");
        require(recipient != address(0), "Zero address target");
        require(address(this).balance >= amount, "Insufficient treasury");
        payable(recipient).transfer(amount);
        proposalCounter++;
        emit ProposalExecuted(proposalCounter);
    }

    receive() external payable {}

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
