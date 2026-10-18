// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MultiSigSigner_200897 {
    address[] public signers;
    mapping(address => bool) public isSigner;
    uint256 public requiredConfirmations;

    constructor(address[] memory _signers, uint256 _required) {
        require(_required > 0 && _required <= _signers.length, "Invalid threshold");
        for (uint256 i = 0; i < _signers.length; i++) {
            isSigner[_signers[i]] = true;
            signers.push(_signers[i]);
        }
        requiredConfirmations = _required;
    }

    function confirmAndExecute(address target, uint256 amount) external {
        require(isSigner[msg.sender], "Not authorized signer");
        require(address(this).balance >= amount, "Overdraft");
        (bool success, ) = payable(target).call{value: amount}("");
        require(success, "MultiSig transfer failed");
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
