import os
import random
import shutil
import zipfile
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION & TARGET SETUP (10,000 BALANCED DIVERSE GO CONTRACTS)
# ==============================================================================
OUTPUT_ROOT = Path("dataset/Go")
ZIP_OUTPUT = Path("dataset_go.zip")

TARGET_SAFE_TOTAL = 5000
TARGET_VULN_PER_CLASS = 1000  # 1000 * 5 = 5000 Total Vulnerable
RATIO_FOLDERLESS = 0.5        # 50% Single File, 50% Multi-File Go Modules

VULN_CLASSES = [
    "non_deterministic_execution",
    "concurrency_race_condition",
    "unchecked_state_read_error",
    "access_control",
    "integer_overflow"
]

# Random seed for reproducible generation
random.seed(42)

# ==============================================================================
# 2. DYNAMIC BENIGN HELPER POOL (RANDOMIZED AST COMPLEXITY INJECTION)
# ==============================================================================
# Injected randomly into BOTH Safe and Vulnerable contracts to eliminate
# graph-size, length, and branching shortcuts for GNNs.

BENIGN_HELPERS = [
    """func verifyValidAddress(target string) bool {
\tif len(target) == 0 || target == "0x0" {
\t\treturn false
\t}
\treturn true
}""",

    """func computeProtocolFee(amount uint64, feeBps uint64) (uint64, error) {
\tif amount == 0 || feeBps == 0 {
\t\treturn 0, nil
\t}
\tfee := (amount * feeBps) / 10000
\treturn fee, nil
}""",

    """func calculateVolumeTier(volume uint64) uint8 {
\tif volume > 100000000000 {
\t\treturn 15
\t} else if volume > 10000000000 {
\t\treturn 5
\t}
\treturn 0
}""",

    """func getContractVersion() string {
\treturn "v2.5.0-fabric-chaincode-go"
}""",

    """func getProtocolHealth() bool {
\treturn true
}""",

    """func checkOperationalState(stateId uint32) bool {
\tif stateId == 0 {
\t\treturn false
\t}
\treturn stateId < 100
}""",

    """func clampRate(rate uint64, maxRate uint64) uint64 {
\tif rate > maxRate {
\t\treturn maxRate
\t}
\treturn rate
}""",

    """func isBalanceSufficient(currentBalance uint64, required uint64) bool {
\treturn currentBalance >= required
}"""
]

def sample_helpers():
    k = random.randint(0, 3)
    return "\n\n" + "\n\n".join(random.sample(BENIGN_HELPERS, k)) if k > 0 else ""

def sample_docstring(title):
    headers = [
        f"// =======================================================\n// {title.upper()}\n// Core operational logic for decentralized Go chaincode.\n// =======================================================\n",
        f"/*\n * Package contract implements {title}\n * Decentralized execution module with verified state management.\n */\n",
        f"// {title} provides high-throughput verifiable state transactions.\n"
    ]
    return random.choice(headers) if random.random() < 0.7 else ""

# ==============================================================================
# 3. DIVERSE SAFE GO CONTRACT TEMPLATES (8 BALANCED ARCHETYPES)
# ==============================================================================
def get_safe_template(cid):
    archetype = random.randint(1, 8)
    helpers = sample_helpers()

    if archetype == 1:
        # Archetype 1: Secured Vault with Checked Math & Deterministic State
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"encoding/json"
\t"fmt"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"SafeVault_{cid}")}type SafeVault_{cid} struct {{
}}

type UserBalance struct {{
\tOwner   string `json:"owner"`
\tBalance uint64 `json:"balance"`
}}

func (t *SafeVault_{cid}) Init(stub shim.ChaincodeStubInterface) peer.Response {{
\treturn shim.Success(nil)
}}

func (t *SafeVault_{cid}) Deposit(stub shim.ChaincodeStubInterface, args []string) peer.Response {{
\tif len(args) < 2 {{
\t\treturn shim.Error("Invalid argument count")
\t}}
\tuser := args[0]
\tvar amount uint64
\tfmt.Sscanf(args[1], "%d", &amount)
\tif amount == 0 {{
\t\treturn shim.Error("Zero deposit rejected")
\t}}

\tvalBytes, err := stub.GetState(user)
\tif err != nil {{
\t\treturn shim.Error("Ledger read failure")
\t}}

\tvar record UserBalance
\tif valBytes != nil {{
\t\tif err := json.Unmarshal(valBytes, &record); err != nil {{
\t\t\treturn shim.Error("Deserialization error")
\t\t}}
\t}} else {{
\t\trecord = UserBalance{{Owner: user, Balance: 0}}
\t}}

\trecord.Balance += amount
\tnewBytes, _ := json.Marshal(record)
\t_ = stub.PutState(user, newBytes)
\treturn shim.Success([]byte("Deposit successful"))
}}

func (t *SafeVault_{cid}) Withdraw(stub shim.ChaincodeStubInterface, args []string) peer.Response {{
\tif len(args) < 2 {{
\t\treturn shim.Error("Invalid argument count")
\t}}
\tuser := args[0]
\tvar amount uint64
\tfmt.Sscanf(args[1], "%d", &amount)

\tvalBytes, err := stub.GetState(user)
\tif err != nil || valBytes == nil {{
\t\treturn shim.Error("User record not found")
\t}}

\tvar record UserBalance
\tif err := json.Unmarshal(valBytes, &record); err != nil {{
\t\treturn shim.Error("Malformed account state")
\t}}

\tif record.Balance < amount {{
\t\treturn shim.Error("Insufficient balance")
\t}}

\trecord.Balance -= amount
\tnewBytes, _ := json.Marshal(record)
\t_ = stub.PutState(user, newBytes)
\treturn shim.Success([]byte("Withdrawal successful"))
}}
{helpers}
"""

    elif archetype == 2:
        # Archetype 2: Staking Pool with Strict Verification
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"encoding/json"
\t"fmt"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"StakingPool_{cid}")}type StakingPool_{cid} struct {{
}}

type StakeRecord struct {{
\tUser   string `json:"user"`
\tStaked uint64 `json:"staked"`
}}

func (t *StakingPool_{cid}) Stake(stub shim.ChaincodeStubInterface, user string, amount uint64) peer.Response {{
\tif amount == 0 {{
\t\treturn shim.Error("Stake amount must be positive")
\t}}
\tdata, err := stub.GetState(user)
\tif err != nil {{
\t\treturn shim.Error("Failed to access staking state")
\t}}
\tvar st StakeRecord
\tif data != nil {{
\t\t_ = json.Unmarshal(data, &st)
\t}} else {{
\t\tst = StakeRecord{{User: user, Staked: 0}}
\t}}
\tst.Staked += amount
\tout, _ := json.Marshal(st)
\t_ = stub.PutState(user, out)
\treturn shim.Success([]byte("Stake confirmed"))
}}

func (t *StakingPool_{cid}) Unstake(stub shim.ChaincodeStubInterface, user string, amount uint64) peer.Response {{
\tdata, err := stub.GetState(user)
\tif err != nil || data == nil {{
\t\treturn shim.Error("No active stake discovered")
\t}}
\tvar st StakeRecord
\t_ = json.Unmarshal(data, &st)
\tif st.Staked < amount {{
\t\treturn shim.Error("Exceeds current stake")
\t}}
\tst.Staked -= amount
\tout, _ := json.Marshal(st)
\t_ = stub.PutState(user, out)
\treturn shim.Success([]byte("Unstake confirmed"))
}}
{helpers}
"""

    elif archetype == 3:
        # Archetype 3: Escrow Settlement Contract
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"encoding/json"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"Escrow_{cid}")}type Escrow_{cid} struct {{
}}

type EscrowState struct {{
\tBuyer       string `json:"buyer"`
\tSeller      string `json:"seller"`
\tAmount      uint64 `json:"amount"`
\tIsFinalized bool   `json:"is_finalized"`
}}

func (t *Escrow_{cid}) Release(stub shim.ChaincodeStubInterface, caller string, escrowKey string) peer.Response {{
\tdata, err := stub.GetState(escrowKey)
\tif err != nil || data == nil {{
\t\treturn shim.Error("Escrow key not found")
\t}}
\tvar esc EscrowState
\tif err := json.Unmarshal(data, &esc); err != nil {{
\t\treturn shim.Error("Corrupt state payload")
\t}}
\tif caller != esc.Buyer {{
\t\treturn shim.Error("Unauthorized release: Caller is not the registered buyer")
\t}}
\tif esc.IsFinalized {{
\t\treturn shim.Error("Agreement already finalized")
\t}}
\tesc.IsFinalized = true
\tout, _ := json.Marshal(esc)
\t_ = stub.PutState(escrowKey, out)
\treturn shim.Success([]byte("Escrow released"))
}}
{helpers}
"""

    elif archetype == 4:
        # Archetype 4: Treasury Governor with MSP Verification
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"fmt"
\t"github.com/hyperledger/fabric-chaincode-go/pkg/cid"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"Treasury_{cid}")}type Treasury_{cid} struct {{
}}

func (t *Treasury_{cid}) Disburse(stub shim.ChaincodeStubInterface, target string, amount uint64) peer.Response {{
\tmspID, err := cid.GetMSPID(stub)
\tif err != nil || mspID != "AdminOrgMSP" {{
\t\treturn shim.Error("Access Denied: Only AdminOrgMSP is permitted to disburse funds")
\t}}
\tif len(target) == 0 {{
\t\treturn shim.Error("Zero recipient key")
\t}}
\t_ = stub.PutState(fmt.Sprintf("DISBURSE_%s", target), []byte(fmt.Sprintf("%d", amount)))
\treturn shim.Success([]byte("Disbursement processed"))
}}
{helpers}
"""

    elif archetype == 5:
        # Archetype 5: Standard Fungible Token Ledger
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"encoding/json"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"Token_{cid}")}type Token_{cid} struct {{
}}

func (t *Token_{cid}) Transfer(stub shim.ChaincodeStubInterface, sender string, recipient string, amount uint64) peer.Response {{
\tif len(sender) == 0 || len(recipient) == 0 {{
\t\treturn shim.Error("Invalid account keys")
\t}}
\tsenderBytes, err := stub.GetState(sender)
\tif err != nil || senderBytes == nil {{
\t\treturn shim.Error("Sender account missing")
\t}}
\tvar senderBal uint64
\t_ = json.Unmarshal(senderBytes, &senderBal)
\tif senderBal < amount {{
\t\treturn shim.Error("Low token balance")
\t}}

\trecipientBytes, _ := stub.GetState(recipient)
\tvar recipientBal uint64
\tif recipientBytes != nil {{
\t\t_ = json.Unmarshal(recipientBytes, &recipientBal)
\t}}

\tsenderBal -= amount
\trecipientBal += amount

\tsOut, _ := json.Marshal(senderBal)
\trOut, _ := json.Marshal(recipientBal)
\t_ = stub.PutState(sender, sOut)
\t_ = stub.PutState(recipient, rOut)
\treturn shim.Success([]byte("Transfer verified"))
}}
{helpers}
"""

    elif archetype == 6:
        # Archetype 6: Multi-Signature Approval Channel
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"encoding/json"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"MultiSig_{cid}")}type MultiSig_{cid} struct {{
}}

type Proposal struct {{
\tSignerOne string `json:"signer_one"`
\tSignerTwo string `json:"signer_two"`
\tConfirmedA bool  `json:"confirmed_a"`
\tConfirmedB bool  `json:"confirmed_b"`
\tExecuted   bool  `json:"executed"`
}}

func (t *MultiSig_{cid}) ExecuteProposal(stub shim.ChaincodeStubInterface, id string) peer.Response {{
\tdata, err := stub.GetState(id)
\tif err != nil || data == nil {{
\t\treturn shim.Error("Proposal does not exist")
\t}}
\tvar p Proposal
\t_ = json.Unmarshal(data, &p)
\tif !p.ConfirmedA || !p.ConfirmedB {{
\t\treturn shim.Error("Requires consensus from both verified signers")
\t}}
\tif p.Executed {{
\t\treturn shim.Error("Proposal already executed")
\t}}
\tp.Executed = true
\tout, _ := json.Marshal(p)
\t_ = stub.PutState(id, out)
\treturn shim.Success([]byte("Proposal finalized"))
}}
{helpers}
"""

    elif archetype == 7:
        # Archetype 7: Liquidity Pool
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"encoding/json"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"LiquidityPool_{cid}")}type LiquidityPool_{cid} struct {{
}}

type PoolReserve struct {{
\tReserveA uint64 `json:"reserve_a"`
\tReserveB uint64 `json:"reserve_b"`
}}

func (t *LiquidityPool_{cid}) SyncReserves(stub shim.ChaincodeStubInterface, addA uint64, addB uint64) peer.Response {{
\tdata, _ := stub.GetState("POOL_RESERVES")
\tvar res PoolReserve
\tif data != nil {{
\t\t_ = json.Unmarshal(data, &res)
\t}}
\tres.ReserveA += addA
\tres.ReserveB += addB
\tout, _ := json.Marshal(res)
\t_ = stub.PutState("POOL_RESERVES", out)
\treturn shim.Success([]byte("Reserves synchronized"))
}}
{helpers}
"""

    else:
        # Archetype 8: Deterministic Timed Vesting (Using stub.GetTxTimestamp)
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"encoding/json"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"TimedVesting_{cid}")}type TimedVesting_{cid} struct {{
}}

type VestingSchedule struct {{
\tBeneficiary   string `json:"beneficiary"`
\tCliffEpoch    int64  `json:"cliff_epoch"`
\tAmount        uint64 `json:"amount"`
\tIsVested      bool   `json:"is_vested"`
}}

func (t *TimedVesting_{cid}) Claim(stub shim.ChaincodeStubInterface, id string) peer.Response {{
\tdata, err := stub.GetState(id)
\tif err != nil || data == nil {{
\t\treturn shim.Error("Vesting record not found")
\t}}
\tvar v VestingSchedule
\t_ = json.Unmarshal(data, &v)

\ttxTime, err := stub.GetTxTimestamp()
\tif err != nil {{
\t\treturn shim.Error("Unable to extract transaction timestamp")
\t}}

\tif txTime.Seconds < v.CliffEpoch {{
\t\treturn shim.Error("Cliff deadline has not been reached")
\t}}
\tif v.IsVested {{
\t\treturn shim.Error("Already claimed")
\t}}
\tv.IsVested = true
\tout, _ := json.Marshal(v)
\t_ = stub.PutState(id, out)
\treturn shim.Success([]byte("Vested allocation released"))
}}
{helpers}
"""

# ==============================================================================
# 4. DIVERSE VULNERABLE GO CONTRACT TEMPLATES (5 CLASSES x SUB-TYPES)
# ==============================================================================
def get_vulnerable_template(vuln_type, cid):
    helpers = sample_helpers()

    if vuln_type == "non_deterministic_execution":
        # Flaw: Using system clock time.Now() or rand.Intn() inside chaincode state transaction
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"fmt"
\t"math/rand"
\t"time"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"VulnNonDet_{cid}")}type VulnNonDeterministic_{cid} struct {{
}}

func (t *VulnNonDeterministic_{cid}) RecordTransaction(stub shim.ChaincodeStubInterface, user string) peer.Response {{
\t// Flaw: time.Now() causes non-deterministic ledger state across validating peer nodes!
\tcurrentTimestamp := time.Now().UnixNano()
\trandFactor := rand.Intn(100)
\tpayload := fmt.Sprintf("TIME:%d_RAND:%d", currentTimestamp, randFactor)
\t_ = stub.PutState(user, []byte(payload))
\treturn shim.Success([]byte(payload))
}}
{helpers}
"""

    elif vuln_type == "concurrency_race_condition":
        # Flaw: Spawning uncoordinated goroutines writing to global or uncommitted state
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"sync"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"VulnRace_{cid}")}type VulnRaceCondition_{cid} struct {{
}}

var globalSharedBalance uint64
var raceMutex sync.Mutex

func (t *VulnRaceCondition_{cid}) BatchProcess(stub shim.ChaincodeStubInterface, delta uint64) peer.Response {{
\t// Flaw: Unbounded background goroutine mutating shared state without transactional consensus
\tgo func() {{
\t\tglobalSharedBalance += delta
\t\t_ = stub.PutState("GLOBAL_BALANCE", []byte("DIRTY_READ"))
\t}}()
\treturn shim.Success([]byte("Batch scheduled"))
}}
{helpers}
"""

    elif vuln_type == "unchecked_state_read_error":
        # Flaw: Discarding err and dereferencing nil slice leading to runtime panic/crash
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"strconv"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"VulnUnchecked_{cid}")}type VulnUncheckedRead_{cid} struct {{
}}

func (t *VulnUncheckedRead_{cid}) DebitAccount(stub shim.ChaincodeStubInterface, account string, amount int) peer.Response {{
\t// Flaw: Discarding error and blindly indexing raw data slice without nil check
\tdata, _ := stub.GetState(account)
\tval, _ := strconv.Atoi(string(data))
\tval -= amount
\t_ = stub.PutState(account, []byte(strconv.Itoa(val)))
\treturn shim.Success([]byte("Account debited"))
}}
{helpers}
"""

    elif vuln_type == "access_control":
        # Flaw: Missing caller verification or MSP check on critical administrative methods
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"VulnAccess_{cid}")}type VulnAccessControl_{cid} struct {{
}}

func (t *VulnAccessControl_{cid}) ResetContractState(stub shim.ChaincodeStubInterface, wipeKey string) peer.Response {{
\t// Flaw: Anyone can invoke this administrative function; missing cid.GetMSPID verification!
\t_ = stub.DelState(wipeKey)
\treturn shim.Success([]byte("State reset confirmed"))
}}

func (t *VulnAccessControl_{cid}) MintUnrestricted(stub shim.ChaincodeStubInterface, target string, amount string) peer.Response {{
\t// Flaw: Missing authorization guard
\t_ = stub.PutState(target, []byte(amount))
\treturn shim.Success([]byte("Minted"))
}}
{helpers}
"""

    else: # integer_overflow
        # Flaw: Unchecked arithmetic wrapping
        return f"""// SPDX-License-Identifier: MIT
package main

import (
\t"fmt"
\t"github.com/hyperledger/fabric-chaincode-go/shim"
\t"github.com/hyperledger/fabric-protos-go/peer"
)

{sample_docstring(f"VulnOvf_{cid}")}type VulnOverflow_{cid} struct {{
}}

func (t *VulnOverflow_{cid}) BatchMintBonus(stub shim.ChaincodeStubInterface, account string, count uint64, perUnit uint64) peer.Response {{
\t// Flaw: Unchecked uint64 multiplication wraps to small number, bypassing balance thresholds
\ttotalBonus := count * perUnit
\t_ = stub.PutState(account, []byte(fmt.Sprintf("%d", totalBonus)))
\treturn shim.Success([]byte("Bonus minted"))
}}
{helpers}
"""

# ==============================================================================
# 5. MULTI-FILE PROJECT GENERATION (GO MODULE LAYOUT)
# ==============================================================================
def generate_multi_file_project(is_safe, vuln_type, contract_id):
    if is_safe:
        main_code = get_safe_template(contract_id)
    else:
        main_code = get_vulnerable_template(vuln_type, contract_id)

    proj_files = {
        "go.mod": f"""module chaincode_project_{contract_id}

go 1.20

require (
\tgithub.com/hyperledger/fabric-chaincode-go v0.0.0-20230228194215-b8425e838495
\tgithub.com/hyperledger/fabric-protos-go v0.3.0
)
""",
        "main.go": main_code,
        "state.go": f"""// SPDX-License-Identifier: MIT
package main

type ConfigState_{contract_id} struct {{
\tAdminAddress string `json:"admin_address"`
\tIsPaused     bool   `json:"is_paused"`
\tFeeRate      uint64 `json:"fee_rate"`
}}
""",
        "utils.go": f"""// SPDX-License-Identifier: MIT
package main

func SafeCalculateShare(principal uint64, bps uint64) (uint64, bool) {{
\tif bps > 10000 {{
\t\treturn 0, false
\t}}
\treturn (principal * bps) / 10000, true
}}
"""
    }

    if random.random() < 0.6:
        proj_files["errors.go"] = f"""// SPDX-License-Identifier: MIT
package main

import "errors"

var (
\tErrUnauthorizedAccess = errors.New("unauthorized caller access")
\tErrMathComputation     = errors.New("arithmetic calculation error")
)
"""

    return proj_files

# ==============================================================================
# 6. MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    print("=" * 80)
    print("GO (FABRIC/COSMOS CHAINCODE) 10,000 BALANCED DATASET GENERATION PIPELINE")
    print(f"Target Destination: {OUTPUT_ROOT.resolve()}")
    print("=" * 80)

    # Directory Structure
    safe_folderless_dir = OUTPUT_ROOT / "safe" / "folderless"
    safe_folderwise_dir = OUTPUT_ROOT / "safe" / "folderwise"
    vuln_folderless_dir = OUTPUT_ROOT / "vulnerable" / "folderless"
    vuln_folderwise_dir = OUTPUT_ROOT / "vulnerable" / "folderwise"

    # Reset output directory
    if OUTPUT_ROOT.exists():
        print(f"[*] Removing existing output directory '{OUTPUT_ROOT}'...")
        shutil.rmtree(OUTPUT_ROOT)

    safe_folderless_dir.mkdir(parents=True, exist_ok=True)
    safe_folderwise_dir.mkdir(parents=True, exist_ok=True)

    for v in VULN_CLASSES:
        (vuln_folderless_dir / v).mkdir(parents=True, exist_ok=True)
        (vuln_folderwise_dir / v).mkdir(parents=True, exist_ok=True)

    cid_counter = 100000

    # 1. Generate Safe Single-File Programs (2,500)
    print("[*] Generating 2,500 Safe Single-File Go Contracts...")
    for _ in range(int(TARGET_SAFE_TOTAL * RATIO_FOLDERLESS)):
        code = get_safe_template(cid_counter)
        with open(safe_folderless_dir / f"safe_contract_{cid_counter}.go", "w", encoding="utf-8") as f:
            f.write(code)
        cid_counter += 1

    # 2. Generate Safe Folder-Wise Go Modules (2,500)
    print("[*] Generating 2,500 Safe Folder-Wise Go Projects...")
    for _ in range(int(TARGET_SAFE_TOTAL * (1 - RATIO_FOLDERLESS))):
        proj_dir = safe_folderwise_dir / f"safe_project_{cid_counter}"
        files = generate_multi_file_project(is_safe=True, vuln_type=None, contract_id=cid_counter)
        for rel_path, content in files.items():
            full_path = proj_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        cid_counter += 1

    # 3. Generate Vulnerable Single-File Contracts (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Single-File Go Contracts (500 x 5 classes)...")
    for v in VULN_CLASSES:
        for _ in range(int(TARGET_VULN_PER_CLASS * RATIO_FOLDERLESS)):
            code = get_vulnerable_template(v, cid_counter)
            with open(vuln_folderless_dir / v / f"vuln_{v}_{cid_counter}.go", "w", encoding="utf-8") as f:
                f.write(code)
            cid_counter += 1

    # 4. Generate Vulnerable Folder-Wise Go Modules (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Folder-Wise Go Projects (500 x 5 classes)...")
    for v in VULN_CLASSES:
        for _ in range(int(TARGET_VULN_PER_CLASS * (1 - RATIO_FOLDERLESS))):
            proj_dir = vuln_folderwise_dir / v / f"vuln_project_{v}_{cid_counter}"
            files = generate_multi_file_project(is_safe=False, vuln_type=v, contract_id=cid_counter)
            for rel_path, content in files.items():
                full_path = proj_dir / rel_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            cid_counter += 1

    # 5. Package into standalone dataset_go.zip archive
    print(f"[*] Packaging clean dataset into '{ZIP_OUTPUT}'...")
    if ZIP_OUTPUT.exists():
        ZIP_OUTPUT.unlink()

    with zipfile.ZipFile(ZIP_OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(OUTPUT_ROOT):
            for file in files:
                full_path = Path(root) / file
                arcname = full_path.relative_to(OUTPUT_ROOT.parent)
                z.write(full_path, arcname)

    zip_size_mb = ZIP_OUTPUT.stat().st_size / (1024 * 1024)
    print("=" * 80)
    print("[+] GO DATASET GENERATION & COMPRESSION COMPLETE!")
    print(f"    Total Contracts Created: {cid_counter - 100000}")
    print(f"    - Safe Contracts       : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise)")
    print(f"    - Vulnerable Contracts : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise across 5 classes)")
    print(f"    Folder Structure       : {OUTPUT_ROOT.resolve()}")
    print(f"    Archive Location       : {ZIP_OUTPUT.resolve()} ({zip_size_mb:.2f} MB)")
    print("=" * 80)

if __name__ == "__main__":
    main()
