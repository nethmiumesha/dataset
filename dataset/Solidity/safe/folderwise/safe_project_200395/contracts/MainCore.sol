// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MultiSigSigner_200395 {
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
}
