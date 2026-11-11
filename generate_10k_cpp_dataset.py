import os
import random
import shutil
import zipfile
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION & TARGET SETUP (10,000 BALANCED DIVERSE C++ CONTRACTS)
# ==============================================================================
OUTPUT_ROOT = Path("dataset/C++")
ZIP_OUTPUT = Path("dataset_cpp.zip")

TARGET_SAFE_TOTAL = 5000
TARGET_VULN_PER_CLASS = 1000  # 1000 * 5 = 5000 Total Vulnerable
RATIO_FOLDERLESS = 0.5        # 50% Single File, 50% Multi-File C++ Projects

VULN_CLASSES = [
    "missing_authorization",
    "forged_transfer_notification",
    "buffer_overflow",
    "integer_overflow",
    "missing_table_existence_check"
]

# Random seed for reproducible generation
random.seed(42)

# ==============================================================================
# 2. DYNAMIC BENIGN HELPER POOL (RANDOMIZED AST COMPLEXITY INJECTION)
# ==============================================================================
BENIGN_HELPERS = [
    """    bool verify_account_nonzero(eosio::name target) {
        eosio::check(target.value != 0, "Invalid target account");
        return true;
    }""",

    """    uint64_t compute_protocol_fee(uint64_t amount, uint64_t fee_bps) {
        if (amount == 0 || fee_bps == 0) return 0;
        return (amount * fee_bps) / 10000;
    }""",

    """    uint8_t calculate_volume_tier(uint64_t volume) {
        if (volume > 100000000000ULL) return 15;
        if (volume > 10000000000ULL) return 5;
        return 0;
    }""",

    """    std::string get_contract_version() {
        return "v2.5.0-eosio-wasm-production";
    }""",

    """    bool get_protocol_health() {
        return true;
    }""",

    """    bool check_operational_state(uint32_t state_id) {
        eosio::check(state_id > 0, "Invalid operational state ID");
        return state_id < 100;
    }""",

    """    uint64_t clamp_rate(uint64_t rate, uint64_t max_rate) {
        return (rate > max_rate) ? max_rate : rate;
    }"""
]

def sample_helpers():
    k = random.randint(0, 3)
    return "\n\n" + "\n\n".join(random.sample(BENIGN_HELPERS, k)) if k > 0 else ""

def sample_docstring(title):
    headers = [
        f"// =======================================================\n// {title.upper()}\n// Core operational logic for decentralized EOSIO C++ smart contract.\n// =======================================================\n",
        f"/**\n * @file {title}.cpp\n * @dev Decentralized WebAssembly contract with verified state management.\n */\n",
        f"// {title} provides high-performance on-chain execution.\n"
    ]
    return random.choice(headers) if random.random() < 0.7 else ""

# ==============================================================================
# 3. DIVERSE SAFE C++ CONTRACT TEMPLATES (8 BALANCED ARCHETYPES)
# ==============================================================================
def get_safe_template(cid):
    archetype = random.randint(1, 8)
    helpers = sample_helpers()

    if archetype == 1:
        # Archetype 1: Secured Vault with require_auth & Multi-Index Table
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>
#include <eosio/asset.hpp>

{sample_docstring(f"SafeVault_{cid}")}class [[eosio::contract("safe_vault_{cid}")]] safe_vault_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] account_record {{
        eosio::name owner;
        eosio::asset balance;
        uint64_t primary_key() const {{ return owner.value; }}
    }};
    typedef eosio::multi_index<"accounts"_n, account_record> accounts_table;

    [[eosio::action]]
    void deposit(eosio::name user, eosio::asset quantity) {{
        require_auth(user);
        eosio::check(quantity.is_valid() && quantity.amount > 0, "Invalid deposit quantity");

        accounts_table accounts(get_self(), get_self().value);
        auto itr = accounts.find(user.value);
        if (itr == accounts.end()) {{
            accounts.emplace(user, [&](auto& row) {{
                row.owner = user;
                row.balance = quantity;
            }});
        }} else {{
            accounts.modify(itr, eosio::same_payer, [&](auto& row) {{
                row.balance += quantity;
            }});
        }}
    }}

    [[eosio::action]]
    void withdraw(eosio::name user, eosio::asset quantity) {{
        require_auth(user);
        eosio::check(quantity.is_valid() && quantity.amount > 0, "Invalid withdrawal quantity");

        accounts_table accounts(get_self(), get_self().value);
        auto itr = accounts.find(user.value);
        eosio::check(itr != accounts.end(), "User account not registered");
        eosio::check(itr->balance.amount >= quantity.amount, "Insufficient vault balance");

        accounts.modify(itr, eosio::same_payer, [&](auto& row) {{
            row.balance -= quantity;
        }});
    }}
{helpers}
}};
"""

    elif archetype == 2:
        # Archetype 2: Staking Pool with Strict Verification
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"StakingPool_{cid}")}class [[eosio::contract("staking_pool_{cid}")]] staking_pool_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] stake_entry {{
        eosio::name user;
        uint64_t staked_amount;
        uint64_t primary_key() const {{ return user.value; }}
    }};
    typedef eosio::multi_index<"stakers"_n, stake_entry> stakers_table;

    [[eosio::action]]
    void stake(eosio::name user, uint64_t amount) {{
        require_auth(user);
        eosio::check(amount > 0, "Stake amount must be non-zero");

        stakers_table stakers(get_self(), get_self().value);
        auto itr = stakers.find(user.value);
        if (itr == stakers.end()) {{
            stakers.emplace(user, [&](auto& row) {{
                row.user = user;
                row.staked_amount = amount;
            }});
        }} else {{
            stakers.modify(itr, eosio::same_payer, [&](auto& row) {{
                row.staked_amount += amount;
            }});
        }}
    }}

    [[eosio::action]]
    void unstake(eosio::name user, uint64_t amount) {{
        require_auth(user);
        stakers_table stakers(get_self(), get_self().value);
        auto itr = stakers.find(user.value);
        eosio::check(itr != stakers.end(), "No active stake record found");
        eosio::check(itr->staked_amount >= amount, "Unstake exceeds registered balance");

        stakers.modify(itr, eosio::same_payer, [&](auto& row) {{
            row.staked_amount -= amount;
        }});
    }}
{helpers}
}};
"""

    elif archetype == 3:
        # Archetype 3: Escrow Settlement Contract
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"Escrow_{cid}")}class [[eosio::contract("escrow_{cid}")]] escrow_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] agreement {{
        uint64_t id;
        eosio::name buyer;
        eosio::name seller;
        uint64_t amount;
        bool finalized;
        uint64_t primary_key() const {{ return id; }}
    }};
    typedef eosio::multi_index<"agreements"_n, agreement> agreements_table;

    [[eosio::action]]
    void release(uint64_t id, eosio::name caller) {{
        agreements_table agreements(get_self(), get_self().value);
        auto itr = agreements.find(id);
        eosio::check(itr != agreements.end(), "Escrow agreement does not exist");
        eosio::check(caller == itr->buyer, "Only registered buyer can release funds");
        require_auth(caller);
        eosio::check(!itr->finalized, "Escrow already finalized");

        agreements.modify(itr, eosio::same_payer, [&](auto& row) {{
            row.finalized = true;
        }});
    }}
{helpers}
}};
"""

    elif archetype == 4:
        # Archetype 4: Treasury Governor with Admin Authentication
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"Treasury_{cid}")}class [[eosio::contract("treasury_{cid}")]] treasury_{cid} : public eosio::contract {{
public:
    using contract::contract;

    [[eosio::action]]
    void disburse(eosio::name recipient, uint64_t amount) {{
        require_auth(get_self());
        eosio::check(recipient.value != 0, "Invalid recipient account");
        eosio::check(amount > 0, "Disbursement amount must be positive");
    }}

    [[eosio::action]]
    void transferadmin(eosio::name new_admin) {{
        require_auth(get_self());
        eosio::check(new_admin.value != 0, "Invalid admin specification");
    }}
{helpers}
}};
"""

    elif archetype == 5:
        # Archetype 5: Standard Fungible Token Contract
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>
#include <eosio/asset.hpp>

{sample_docstring(f"Token_{cid}")}class [[eosio::contract("token_{cid}")]] token_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] account {{
        eosio::asset balance;
        uint64_t primary_key() const {{ return balance.symbol.code().raw(); }}
    }};
    typedef eosio::multi_index<"accounts"_n, account> accounts_table;

    [[eosio::action]]
    void transfer(eosio::name from, eosio::name to, eosio::asset quantity, std::string memo) {{
        eosio::check(from != to, "Cannot transfer to self");
        require_auth(from);
        eosio::check(quantity.is_valid() && quantity.amount > 0, "Must transfer positive quantity");

        accounts_table from_acnts(get_self(), from.value);
        auto from_itr = from_acnts.find(quantity.symbol.code().raw());
        eosio::check(from_itr != from_acnts.end(), "Source account has no tokens");
        eosio::check(from_itr->balance.amount >= quantity.amount, "Overdrawn balance");

        from_acnts.modify(from_itr, from, [&](auto& a) {{
            a.balance -= quantity;
        }});

        accounts_table to_acnts(get_self(), to.value);
        auto to_itr = to_acnts.find(quantity.symbol.code().raw());
        if (to_itr == to_acnts.end()) {{
            to_acnts.emplace(from, [&](auto& a) {{
                a.balance = quantity;
            }});
        }} else {{
            to_acnts.modify(to_itr, eosio::same_payer, [&](auto& a) {{
                a.balance += quantity;
            }});
        }}
    }}
{helpers}
}};
"""

    elif archetype == 6:
        # Archetype 6: Multi-Signature Approval Channel
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"MultiSig_{cid}")}class [[eosio::contract("multisig_{cid}")]] multisig_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] proposal {{
        uint64_t id;
        eosio::name signer_one;
        eosio::name signer_two;
        bool approved_a;
        bool approved_b;
        bool executed;
        uint64_t primary_key() const {{ return id; }}
    }};
    typedef eosio::multi_index<"proposals"_n, proposal> proposals_table;

    [[eosio::action]]
    void execute(uint64_t id) {{
        proposals_table proposals(get_self(), get_self().value);
        auto itr = proposals.find(id);
        eosio::check(itr != proposals.end(), "Proposal not discovered");
        eosio::check(itr->approved_a && itr->approved_b, "Requires dual signer authorization");
        eosio::check(!itr->executed, "Already executed");

        proposals.modify(itr, eosio::same_payer, [&](auto& row) {{
            row.executed = true;
        }});
    }}
{helpers}
}};
"""

    elif archetype == 7:
        # Archetype 7: Liquidity Constant Product Pool
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"LiquidityPool_{cid}")}class [[eosio::contract("liqpool_{cid}")]] liqpool_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] pool_state {{
        uint64_t id;
        uint64_t reserve_a;
        uint64_t reserve_b;
        uint64_t primary_key() const {{ return id; }}
    }};
    typedef eosio::multi_index<"pool"_n, pool_state> pool_table;

    [[eosio::action]]
    void sync(uint64_t add_a, uint64_t add_b) {{
        require_auth(get_self());
        pool_table pool(get_self(), get_self().value);
        auto itr = pool.find(0);
        if (itr == pool.end()) {{
            pool.emplace(get_self(), [&](auto& row) {{
                row.id = 0;
                row.reserve_a = add_a;
                row.reserve_b = add_b;
            }});
        }} else {{
            pool.modify(itr, eosio::same_payer, [&](auto& row) {{
                row.reserve_a += add_a;
                row.reserve_b += add_b;
            }});
        }}
    }}
{helpers}
}};
"""

    else:
        # Archetype 8: Secure Timed Vesting (Using current_time_point)
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>
#include <eosio/system.hpp>

{sample_docstring(f"TimedVesting_{cid}")}class [[eosio::contract("vesting_{cid}")]] vesting_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] schedule {{
        eosio::name beneficiary;
        uint32_t cliff_timestamp;
        uint64_t amount;
        bool claimed;
        uint64_t primary_key() const {{ return beneficiary.value; }}
    }};
    typedef eosio::multi_index<"schedules"_n, schedule> schedules_table;

    [[eosio::action]]
    void claim(eosio::name user) {{
        require_auth(user);
        schedules_table schedules(get_self(), get_self().value);
        auto itr = schedules.find(user.value);
        eosio::check(itr != schedules.end(), "Vesting schedule does not exist");
        
        uint32_t current_time = eosio::current_time_point().sec_since_epoch();
        eosio::check(current_time >= itr->cliff_timestamp, "Cliff period is currently active");
        eosio::check(!itr->claimed, "Tokens already claimed");

        schedules.modify(itr, eosio::same_payer, [&](auto& row) {{
            row.claimed = true;
        }});
    }}
{helpers}
}};
"""

# ==============================================================================
# 4. DIVERSE VULNERABLE C++ CONTRACT TEMPLATES (5 CLASSES x SUB-TYPES)
# ==============================================================================
def get_vulnerable_template(vuln_type, cid):
    helpers = sample_helpers()

    if vuln_type == "missing_authorization":
        # Flaw: Sensitive administrative functions executed without require_auth()
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"VulnAuth_{cid}")}class [[eosio::contract("vuln_auth_{cid}")]] vuln_auth_{cid} : public eosio::contract {{
public:
    using contract::contract;

    [[eosio::action]]
    void drainvault(eosio::name target, uint64_t amount) {{
        // Flaw: Missing require_auth(get_self()) or owner authentication!
        // Anyone can invoke this action and drain contract resources!
        eosio::print("Disbursing funds to arbitrary account");
    }}

    [[eosio::action]]
    void resetconfig() {{
        // Flaw: Unauthenticated configuration reset
        eosio::print("System parameters cleared");
    }}
{helpers}
}};
"""

    elif vuln_type == "forged_transfer_notification":
        # Flaw: Handling transfer notification without verifying get_first_receiver() == "eosio.token"_n
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>
#include <eosio/asset.hpp>

{sample_docstring(f"VulnNotice_{cid}")}class [[eosio::contract("vuln_notice_{cid}")]] vuln_notice_{cid} : public eosio::contract {{
public:
    using contract::contract;

    [[eosio::on_notify("*::transfer")]]
    void on_transfer(eosio::name from, eosio::name to, eosio::asset quantity, std::string memo) {{
        if (from == get_self() || to != get_self()) return;
        // Flaw: Missing check: get_first_receiver() == "eosio.token"_n !
        // Attackers can deploy fake token contracts and credit arbitrary balances!
        eosio::print("Crediting user deposit without verifying authentic token contract");
    }}
{helpers}
}};
"""

    elif vuln_type == "buffer_overflow":
        # Flaw: Raw pointer manipulation, memcpy beyond boundary without bounds checking
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>
#include <cstring>

{sample_docstring(f"VulnBuffer_{cid}")}class [[eosio::contract("vuln_buf_{cid}")]] vuln_buf_{cid} : public eosio::contract {{
public:
    using contract::contract;

    [[eosio::action]]
    void processbytes(std::string payload) {{
        char stack_buffer[32];
        // Flaw: Unbounded strcpy/memcpy from user payload into fixed stack buffer!
        std::memcpy(stack_buffer, payload.c_str(), payload.length());
        eosio::print("Buffer processed: ", stack_buffer);
    }}
{helpers}
}};
"""

    elif vuln_type == "integer_overflow":
        # Flaw: Raw unsigned arithmetic wrapping causing balance wrap-around
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"VulnOvf_{cid}")}class [[eosio::contract("vuln_ovf_{cid}")]] vuln_ovf_{cid} : public eosio::contract {{
public:
    using contract::contract;

    [[eosio::action]]
    void batchmint(eosio::name user, uint64_t count, uint64_t per_item) {{
        // Flaw: Unchecked uint64 multiplication wraps to 0 or tiny number
        uint64_t total_required = count * per_item;
        eosio::print("Mint calculation wrapped: ", total_required);
    }}
{helpers}
}};
"""

    else: # missing_table_existence_check
        # Flaw: Modifying or dereferencing table iterator without verifying itr != table.end()
        return f"""// SPDX-License-Identifier: MIT
#include <eosio/eosio.hpp>

{sample_docstring(f"VulnTable_{cid}")}class [[eosio::contract("vuln_tbl_{cid}")]] vuln_tbl_{cid} : public eosio::contract {{
public:
    using contract::contract;

    struct [[eosio::table]] item_entry {{
        uint64_t id;
        uint64_t score;
        uint64_t primary_key() const {{ return id; }}
    }};
    typedef eosio::multi_index<"items"_n, item_entry> items_table;

    [[eosio::action]]
    void updatescore(uint64_t id, uint64_t new_score) {{
        items_table items(get_self(), get_self().value);
        auto itr = items.find(id);
        // Flaw: Missing eosio::check(itr != items.end(), "Item not found")!
        // Calling modify on an end iterator causes memory corruption or contract assertion failure
        items.modify(itr, eosio::same_payer, [&](auto& row) {{
            row.score = new_score;
        }});
    }}
{helpers}
}};
"""

# ==============================================================================
# 5. MULTI-FILE PROJECT GENERATION (CMAKE PROJECT LAYOUT)
# ==============================================================================
def generate_multi_file_project(is_safe, vuln_type, contract_id):
    if is_safe:
        main_code = get_safe_template(contract_id)
    else:
        main_code = get_vulnerable_template(vuln_type, contract_id)

    proj_files = {
        "CMakeLists.txt": f"""cmake_minimum_required(VERSION 3.5)
project(eosio_project_{contract_id} VERSION 1.0.0)

find_package(eosio.cdt REQUIRED)

add_contract(eosio_project_{contract_id} eosio_project_{contract_id}
    src/main.cpp
)

target_include_directories(eosio_project_{contract_id} PUBLIC include)
""",
        "src/main.cpp": main_code,
        "include/types.hpp": f"""// SPDX-License-Identifier: MIT
#pragma once
#include <eosio/eosio.hpp>

namespace project_{contract_id} {{
    struct config_data {{
        eosio::name admin;
        bool is_paused;
        uint64_t fee_rate;
    }};
}}
""",
        "include/utils.hpp": f"""// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>

namespace project_{contract_id} {{
    inline uint64_t safe_calc_share(uint64_t principal, uint64_t bps) {{
        if (bps > 10000) return 0;
        return (principal * bps) / 10000;
    }}
}}
"""
    }

    if random.random() < 0.6:
        proj_files["include/errors.hpp"] = f"""// SPDX-License-Identifier: MIT
#pragma once

namespace project_{contract_id}::errors {{
    constexpr const char* ACCESS_DENIED = "Access Denied: Unauthorized caller";
    constexpr const char* OVERFLOW_DETECTED = "Arithmetic computation overflowed";
}}
"""

    return proj_files

# ==============================================================================
# 6. MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    print("=" * 80)
    print("C++ (EOSIO / WASM SMART CONTRACTS) 10,000 BALANCED DATASET GENERATION PIPELINE")
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
    print("[*] Generating 2,500 Safe Single-File C++ Contracts...")
    for _ in range(int(TARGET_SAFE_TOTAL * RATIO_FOLDERLESS)):
        code = get_safe_template(cid_counter)
        with open(safe_folderless_dir / f"safe_contract_{cid_counter}.cpp", "w", encoding="utf-8") as f:
            f.write(code)
        cid_counter += 1

    # 2. Generate Safe Folder-Wise C++ Projects (2,500)
    print("[*] Generating 2,500 Safe Folder-Wise C++ Projects...")
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
    print("[*] Generating 2,500 Vulnerable Single-File C++ Contracts (500 x 5 classes)...")
    for v in VULN_CLASSES:
        for _ in range(int(TARGET_VULN_PER_CLASS * RATIO_FOLDERLESS)):
            code = get_vulnerable_template(v, cid_counter)
            with open(vuln_folderless_dir / v / f"vuln_{v}_{cid_counter}.cpp", "w", encoding="utf-8") as f:
                f.write(code)
            cid_counter += 1

    # 4. Generate Vulnerable Folder-Wise C++ Projects (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Folder-Wise C++ Projects (500 x 5 classes)...")
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

    # 5. Package into standalone dataset_cpp.zip archive
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
    print("[+] C++ DATASET GENERATION & COMPRESSION COMPLETE!")
    print(f"    Total Contracts Created: {cid_counter - 100000}")
    print(f"    - Safe Contracts       : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise)")
    print(f"    - Vulnerable Contracts : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise across 5 classes)")
    print(f"    Folder Structure       : {OUTPUT_ROOT.resolve()}")
    print(f"    Archive Location       : {ZIP_OUTPUT.resolve()} ({zip_size_mb:.2f} MB)")
    print("=" * 80)

if __name__ == "__main__":
    main()
