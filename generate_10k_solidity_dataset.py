import os
import random
import re
import shutil
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION & TARGET SETUP (10,000 TOTAL CONTRACTS)
# ==============================================================================
OUTPUT_ROOT = r"dataset/Solidity"
OLD_RAW_DIR = r"data/raw/Solidity"  # පැරණි raw dataset එකේ path එක

# Safe 5,000 ක් සහ Vulnerable 5,000 ක් (කාණ්ඩ 5 න් එකකට 1,000 බැගින්)
TARGET_SAFE_TOTAL = 5000
TARGET_VULN_PER_CLASS = 1000  # 1000 * 5 = 5000 Total Vulnerable

# 50% Folderless (Single files) සහ 50% Folderwise (Nested projects)
RATIO_FOLDERLESS = 0.5

VULN_CLASSES = [
    "reentrancy",
    "access_control",
    "integer_overflow",
    "unchecked_low_level_calls",
    "timestamp_dependence"
]

# ==============================================================================
# 2. VULNERABILITY DETECTION SIGNATURES
# ==============================================================================
SIGNATURES = {
    "reentrancy": [r"\.call\s*\{?\s*value\s*:", r"\.call\.value\(", r"\.call\("],
    "access_control": [r"selfdestruct\s*\(", r"suicide\s*\(", r"tx\.origin"],
    "integer_overflow": [r"\+\+", r"\+\=", r"\-\=", r"\*\="],
    "unchecked_low_level_calls": [r"\.send\(", r"\.transfer\(", r"\.delegatecall\("],
    "timestamp_dependence": [r"block\.timestamp", r"\bnow\b", r"block\.number"]
}

def detect_vulnerability(code_text):
    c_low = code_text.lower()
    for vuln, patterns in SIGNATURES.items():
        for pat in patterns:
            if re.search(pat, c_low):
                if vuln == "integer_overflow" and ("safemath" in c_low or "pragma solidity ^0.8" in c_low):
                    continue
                if vuln == "reentrancy" and ("nonreentrant" in c_low or "reentrancyguard" in c_low):
                    continue
                return vuln
    return "safe"

# ==============================================================================
# 3. CODE GENERATION TEMPLATES
# ==============================================================================
def get_code_template(vuln_type, contract_id):
    if vuln_type == "reentrancy":
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract LiquidityVault_{contract_id} {{
    mapping(address => uint256) public userBalances;

    function deposit() public payable {{
        userBalances[msg.sender] += msg.value;
    }}

    function withdrawAll() public {{
        uint256 amount = userBalances[msg.sender];
        require(amount > 0, "Zero balance");
        (bool success, ) = msg.sender.call{{value: amount}}("");
        require(success, "Failed execution");
        userBalances[msg.sender] = 0;
    }}
}}
"""
    elif vuln_type == "access_control":
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VaultController_{contract_id} {{
    address public admin;

    constructor() {{
        admin = msg.sender;
    }}

    function destroyEmergency() external {{
        // Missing onlyOwner or access restriction
        selfdestruct(payable(msg.sender));
    }}
}}
"""
    elif vuln_type == "integer_overflow":
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract StakingRewards_{contract_id} {{
    mapping(address => uint256) public lockTimestamp;

    function extendLock(uint256 additionalSeconds) external {{
        lockTimestamp[msg.sender] += additionalSeconds;
    }}
}}
"""
    elif vuln_type == "unchecked_low_level_calls":
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DividendDistributor_{contract_id} {{
    function distributeFunds(address[] calldata investors) external payable {{
        for (uint256 i = 0; i < investors.length; i++) {{
            investors[i].call{{value: 1 ether}}("");
        }}
    }}
}}
"""
    elif vuln_type == "timestamp_dependence":
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LotteryRound_{contract_id} {{
    function drawJackpot() external payable {{
        require(msg.value >= 1 ether);
        if (block.timestamp % 17 == 0) {{
            payable(msg.sender).transfer(address(this).balance);
        }}
    }}
}}
"""
    else:  # SAFE
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

abstract contract SecurityGuard_{contract_id} {{
    uint256 private _status;
    modifier nonReentrant() {{
        require(_status != 2, "Reentrant call");
        _status = 2;
        _;
        _status = 1;
    }}
}}

contract SafeVault_{contract_id} is SecurityGuard_{contract_id} {{
    mapping(address => uint256) private balances;
    address public immutable owner;

    constructor() {{
        owner = msg.sender;
    }}

    function deposit() external payable {{
        balances[msg.sender] += msg.value;
    }}

    function withdraw(uint256 amount) external nonReentrant {{
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        (bool ok, ) = payable(msg.sender).call{{value: amount}}("");
        require(ok, "Transfer failed");
    }}
}}
"""

def generate_multi_file_project(vuln_type, contract_id):
    main_code = get_code_template(vuln_type, contract_id)
    
    interface_code = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IProtocolInterface_{contract_id} {{
    function executeAction(address account, uint256 amount) external returns (bool);
    function getBalance(address target) external view returns (uint256);
}}
"""
    library_code = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

library MathExtension_{contract_id} {{
    function computeShare(uint256 principal, uint256 rate) internal pure returns (uint256) {{
        return (principal * rate) / 10000;
    }}
}}
"""
    helper_code = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_{contract_id} {{
    function _msgSender() internal view returns (address) {{
        return msg.sender;
    }}
}}
"""
    return {
        "contracts/MainCore.sol": main_code,
        "interfaces/IProtocolInterface.sol": interface_code,
        "libraries/MathExtension.sol": library_code,
        "helpers/ContextHelper.sol": helper_code
    }

# ==============================================================================
# 4. EXECUTION PIPELINE
# ==============================================================================
def main():
    print("=" * 80)
    print("GENERATING 10,000 SOLIDITY SMART CONTRACT DATASET")
    print("Categories: Safe & Vulnerable across Folderless and Folderwise structures")
    print("=" * 80)

    base_path = Path(OUTPUT_ROOT)
    
    safe_folderless_dir = base_path / "safe" / "folderless"
    safe_folderwise_dir = base_path / "safe" / "folderwise"
    vuln_folderless_dir = base_path / "vulnerable" / "folderless"
    vuln_folderwise_dir = base_path / "vulnerable" / "folderwise"

    safe_folderless_dir.mkdir(parents=True, exist_ok=True)
    safe_folderwise_dir.mkdir(parents=True, exist_ok=True)

    for v in VULN_CLASSES:
        (vuln_folderless_dir / v).mkdir(parents=True, exist_ok=True)
        (vuln_folderwise_dir / v).mkdir(parents=True, exist_ok=True)

    counts = {
        "safe_folderless": 0,
        "safe_folderwise": 0,
        "vuln_folderless": {v: 0 for v in VULN_CLASSES},
        "vuln_folderwise": {v: 0 for v in VULN_CLASSES}
    }

    # Step 1: Scan old files (පැරණි දත්ත ඇත්නම් ඒවායින් ගෙන වෙන් කිරීම)
    if os.path.exists(OLD_RAW_DIR):
        print(f"[*] Scanning existing data from: {OLD_RAW_DIR}")
        for root, _, files in os.walk(OLD_RAW_DIR):
            for file in files:
                if file.endswith(".sol"):
                    fpath = os.path.join(root, file)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fl:
                            code = fl.read()
                        
                        vtype = detect_vulnerability(code)
                        is_fless = (random.random() < RATIO_FOLDERLESS)

                        if vtype == "safe":
                            if is_fless and counts["safe_folderless"] < int(TARGET_SAFE_TOTAL * RATIO_FOLDERLESS):
                                shutil.copy(fpath, safe_folderless_dir / f"existing_{file}")
                                counts["safe_folderless"] += 1
                            elif not is_fless and counts["safe_folderwise"] < int(TARGET_SAFE_TOTAL * (1 - RATIO_FOLDERLESS)):
                                pdir = safe_folderwise_dir / f"proj_existing_{file[:-4]}"
                                (pdir / "contracts").mkdir(parents=True, exist_ok=True)
                                shutil.copy(fpath, pdir / "contracts" / file)
                                counts["safe_folderwise"] += 1
                        else:
                            if is_fless and counts["vuln_folderless"][vtype] < int(TARGET_VULN_PER_CLASS * RATIO_FOLDERLESS):
                                shutil.copy(fpath, vuln_folderless_dir / vtype / f"existing_{file}")
                                counts["vuln_folderless"][vtype] += 1
                            elif not is_fless and counts["vuln_folderwise"][vtype] < int(TARGET_VULN_PER_CLASS * (1 - RATIO_FOLDERLESS)):
                                pdir = vuln_folderwise_dir / vtype / f"proj_existing_{file[:-4]}"
                                (pdir / "contracts").mkdir(parents=True, exist_ok=True)
                                shutil.copy(fpath, pdir / "contracts" / file)
                                counts["vuln_folderwise"][vtype] += 1
                    except Exception:
                        pass

    # Step 2: හිඟ දත්ත 10,000 සම්පූර්ණ වන තෙක් generate කිරීම
    print("\n[*] Generating balance contracts to reach exactly 10,000...")
    
    target_safe_fless = int(TARGET_SAFE_TOTAL * RATIO_FOLDERLESS)
    target_safe_fwise = int(TARGET_SAFE_TOTAL * (1 - RATIO_FOLDERLESS))

    while counts["safe_folderless"] < target_safe_fless:
        cid = random.randint(100000, 999999)
        code = get_code_template("safe", cid)
        fname = safe_folderless_dir / f"safe_contract_{cid}.sol"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(code)
        counts["safe_folderless"] += 1

    while counts["safe_folderwise"] < target_safe_fwise:
        cid = random.randint(100000, 999999)
        proj_dict = generate_multi_file_project("safe", cid)
        pdir = safe_folderwise_dir / f"safe_project_{cid}"
        for rel_path, c_str in proj_dict.items():
            fpath = pdir / rel_path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(c_str)
        counts["safe_folderwise"] += 1

    target_vuln_fless = int(TARGET_VULN_PER_CLASS * RATIO_FOLDERLESS)
    target_vuln_fwise = int(TARGET_VULN_PER_CLASS * (1 - RATIO_FOLDERLESS))

    for v in VULN_CLASSES:
        while counts["vuln_folderless"][v] < target_vuln_fless:
            cid = random.randint(100000, 999999)
            code = get_code_template(v, cid)
            fname = vuln_folderless_dir / v / f"{v}_contract_{cid}.sol"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(code)
            counts["vuln_folderless"][v] += 1

        while counts["vuln_folderwise"][v] < target_vuln_fwise:
            cid = random.randint(100000, 999999)
            proj_dict = generate_multi_file_project(v, cid)
            pdir = vuln_folderwise_dir / v / f"vuln_project_{v}_{cid}"
            for rel_path, c_str in proj_dict.items():
                fpath = pdir / rel_path
                fpath.parent.mkdir(parents=True, exist_ok=True)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(c_str)
            counts["vuln_folderwise"][v] += 1

    print("\n" + "=" * 80)
    print("SUCCESS: 10,000 SOLIDITY DATASET COMPLETED!")
    print("=" * 80)
    print(f"Safe Folderless (Single files)      : {counts['safe_folderless']}")
    print(f"Safe Folderwise (Nested projects)   : {counts['safe_folderwise']}")
    total_vuln_fless = sum(counts["vuln_folderless"].values())
    total_vuln_fwise = sum(counts["vuln_folderwise"].values())
    print(f"Vuln Folderless (5 Vulnerabilities) : {total_vuln_fless}")
    print(f"Vuln Folderwise (5 Vulnerabilities) : {total_vuln_fwise}")
    print("-" * 80)
    print(f"GRAND TOTAL ROOT ENTRIES           : {counts['safe_folderless'] + counts['safe_folderwise'] + total_vuln_fless + total_vuln_fwise}")
    print("=" * 80)

if __name__ == "__main__":
    main()