// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EscrowAgreement_202340 {
    address public buyer;
    address payable public seller;
    uint256 public lockedAmount;
    bool public isComplete;

    constructor(address payable _seller) payable {
        require(_seller != address(0), "Invalid seller");
        buyer = msg.sender;
        seller = _seller;
        lockedAmount = msg.value;
    }

    function releaseFunds() external {
        require(msg.sender == buyer, "Only buyer can release");
        require(!isComplete, "Already finalized");
        isComplete = true;
        (bool ok, ) = seller.call{value: lockedAmount}("");
        require(ok, "Settlement failed");
    }

    function refundBuyer() external {
        require(msg.sender == buyer, "Unauthorized");
        require(!isComplete, "Settlement finalized");
        isComplete = true;
        payable(buyer).transfer(lockedAmount);
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
