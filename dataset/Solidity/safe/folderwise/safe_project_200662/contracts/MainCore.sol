// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TreasuryGovernor_200662 {
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
}
