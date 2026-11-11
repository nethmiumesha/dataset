import os
import random
import shutil
import zipfile
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION & TARGET SETUP (10,000 BALANCED DIVERSE VYPER CONTRACTS)
# ==============================================================================
OUTPUT_ROOT = Path("dataset/Vyper")
ZIP_OUTPUT = Path("dataset_vyper.zip")

TARGET_SAFE_TOTAL = 5000
TARGET_VULN_PER_CLASS = 1000  # 1000 * 5 = 5000 Total Vulnerable
RATIO_FOLDERLESS = 0.5        # 50% Single File, 50% Multi-Contract Projects

VULN_CLASSES = [
    "reentrancy",
    "access_control",
    "integer_overflow",
    "unchecked_low_level_calls",
    "timestamp_dependence"
]

# Random seed for reproducible generation
random.seed(42)

# ==============================================================================
# 2. DYNAMIC BENIGN HELPER POOL (RANDOMIZED AST COMPLEXITY INJECTION)
# ==============================================================================
# Injected randomly into BOTH Safe and Vulnerable contracts to eliminate
# graph-size, length, and branching shortcuts for GNNs.

BENIGN_HELPERS = [
    """@internal
@pure
def _verify_nonzero_address(target: address) -> bool:
    assert target != empty(address), "Invalid target address"
    return True""",

    """@internal
@pure
def _compute_protocol_fee(amount: uint256, fee_bps: uint256) -> uint256:
    if amount == 0 or fee_bps == 0:
        return 0
    return (amount * fee_bps) // 10000""",

    """@internal
@pure
def _calculate_volume_tier(volume: uint256) -> uint256:
    if volume > 100000000000000000000:
        return 15
    elif volume > 10000000000000000000:
        return 5
    return 0""",

    """@external
@pure
def get_contract_version() -> String[32]:
    return "v2.5.0-vyper-production" """,

    """@external
@pure
def get_protocol_status() -> bool:
    return True""",

    """@internal
@pure
def _check_operational_state(state_id: uint256) -> bool:
    assert state_id > 0, "Invalid state ID"
    return state_id < 100""",

    """@internal
@view
def _is_contract_funded(min_balance: uint256) -> bool:
    return self.balance >= min_balance""",

    """@internal
@pure
def _clamp_rate(rate: uint256, max_rate: uint256) -> uint256:
    if rate > max_rate:
        return max_rate
    return rate"""
]

def sample_helpers():
    k = random.randint(0, 3)
    return "\n\n" + "\n\n".join(random.sample(BENIGN_HELPERS, k)) if k > 0 else ""

def sample_docstring(title):
    headers = [
        f'"""\n@title {title}\n@notice Decentralized execution module with verified state management.\n"""\n',
        f"# @title {title}\n# @notice Core operational logic for decentralized protocol.\n",
        f"# =======================================================\n# {title.upper()}\n# =======================================================\n"
    ]
    return random.choice(headers) if random.random() < 0.7 else ""

# ==============================================================================
# 3. DIVERSE SAFE VYPER CONTRACT TEMPLATES (8 BALANCED ARCHETYPES)
# ==============================================================================
def get_safe_template(cid):
    archetype = random.randint(1, 8)
    helpers = sample_helpers()

    if archetype == 1:
        # Archetype 1: Secured Vault with nonreentrant guard and checks-effects-interactions
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"SafeVault_{cid}")}balances: public(HashMap[address, uint256])
owner: public(address)
is_locked: bool

@deploy
def __init__():
    self.owner = msg.sender

@external
@payable
def deposit():
    assert msg.value > 0, "Zero deposit not allowed"
    self.balances[msg.sender] += msg.value

@external
@nonreentrant
def withdraw(amount: uint256):
    assert self.balances[msg.sender] >= amount, "Insufficient balance"
    # Safe: State update prior to external transfer
    self.balances[msg.sender] -= amount
    raw_call(msg.sender, b"", value=amount)

@external
@view
def get_user_balance(user: address) -> uint256:
    return self.balances[user]{helpers}
"""

    elif archetype == 2:
        # Archetype 2: Staking Pool with Strict Verification
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"StakingPool_{cid}")}staked_amount: public(HashMap[address, uint256])
admin: public(address)
total_staked: public(uint256)

@deploy
def __init__():
    self.admin = msg.sender

@external
@payable
def stake():
    assert msg.value > 0, "Cannot stake 0"
    self.staked_amount[msg.sender] += msg.value
    self.total_staked += msg.value

@external
@nonreentrant
def unstake(amount: uint256):
    assert self.staked_amount[msg.sender] >= amount, "Exceeds staked amount"
    self.staked_amount[msg.sender] -= amount
    self.total_staked -= amount
    send(msg.sender, amount)

@external
@view
def get_staked(user: address) -> uint256:
    return self.staked_amount[user]{helpers}
"""

    elif archetype == 3:
        # Archetype 3: Escrow Settlement Contract
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"EscrowAgreement_{cid}")}buyer: public(address)
seller: public(address)
locked_amount: public(uint256)
is_finalized: public(bool)

@deploy
@payable
def __init__(_seller: address):
    assert _seller != empty(address), "Invalid seller address"
    self.buyer = msg.sender
    self.seller = _seller
    self.locked_amount = msg.value

@external
@nonreentrant
def release_funds():
    assert msg.sender == self.buyer, "Only buyer can release funds"
    assert not self.is_finalized, "Already finalized"
    self.is_finalized = True
    send(self.seller, self.locked_amount)

@external
@view
def get_escrow_status() -> (uint256, bool):
    return (self.locked_amount, self.is_finalized){helpers}
"""

    elif archetype == 4:
        # Archetype 4: Treasury Governor with Role Verification
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"TreasuryGovernor_{cid}")}governor: public(address)
proposal_counter: public(uint256)

@deploy
def __init__():
    self.governor = msg.sender

@external
@payable
def fund_treasury():
    pass

@external
@nonreentrant
def execute_disbursement(recipient: address, amount: uint256):
    assert msg.sender == self.governor, "Unauthorized access: Caller not governor"
    assert recipient != empty(address), "Zero address recipient"
    assert self.balance >= amount, "Insufficient treasury balance"
    send(recipient, amount)
    self.proposal_counter += 1

@external
@view
def get_disbursement_count() -> uint256:
    return self.proposal_counter{helpers}
"""

    elif archetype == 5:
        # Archetype 5: Standard ERC20-Compatible Token Ledger
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"TokenLedger_{cid}")}balance_of: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])
total_supply: public(uint256)
owner: public(address)

@deploy
def __init__(initial_supply: uint256):
    self.owner = msg.sender
    self.total_supply = initial_supply * 10**18
    self.balance_of[msg.sender] = self.total_supply

@external
def transfer(recipient: address, amount: uint256) -> bool:
    assert recipient != empty(address), "Transfer to zero address"
    assert self.balance_of[msg.sender] >= amount, "Balance low"
    self.balance_of[msg.sender] -= amount
    self.balance_of[recipient] += amount
    return True

@external
@view
def get_user_balance(user: address) -> uint256:
    return self.balance_of[user]{helpers}
"""

    elif archetype == 6:
        # Archetype 6: Multi-Signature Execution Channel
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"MultiSigExecutor_{cid}")}signer_one: public(address)
signer_two: public(address)
has_confirmed: public(HashMap[uint256, HashMap[address, bool]])
execution_count: public(uint256)

@deploy
def __init__(_s1: address, _s2: address):
    assert _s1 != empty(address) and _s2 != empty(address), "Invalid signers"
    assert _s1 != _s2, "Signers must be distinct"
    self.signer_one = _s1
    self.signer_two = _s2

@external
@payable
def deposit_reserves():
    pass

@external
def submit_and_confirm(tx_id: uint256):
    assert msg.sender == self.signer_one or msg.sender == self.signer_two, "Not an authorized signer"
    self.has_confirmed[tx_id][msg.sender] = True

@external
@nonreentrant
def execute_transaction(tx_id: uint256, target: address, amount: uint256):
    assert self.has_confirmed[tx_id][self.signer_one], "Signer 1 has not confirmed"
    assert self.has_confirmed[tx_id][self.signer_two], "Signer 2 has not confirmed"
    assert self.balance >= amount, "Insufficient channel funds"
    self.has_confirmed[tx_id][self.signer_one] = False
    self.has_confirmed[tx_id][self.signer_two] = False
    self.execution_count += 1
    send(target, amount){helpers}
"""

    elif archetype == 7:
        # Archetype 7: Liquidity Provider Pool
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"LiquidityPool_{cid}")}lp_shares: public(HashMap[address, uint256])
total_lp_supply: public(uint256)
pool_fee_bps: public(uint256)

@deploy
def __init__():
    self.pool_fee_bps = 30

@external
@payable
def add_liquidity() -> uint256:
    assert msg.value > 0, "Deposit zero value"
    shares: uint256 = msg.value
    self.lp_shares[msg.sender] += shares
    self.total_lp_supply += shares
    return shares

@external
@nonreentrant
def remove_liquidity(shares: uint256) -> uint256:
    assert self.lp_shares[msg.sender] >= shares, "Insufficient shares"
    self.lp_shares[msg.sender] -= shares
    self.total_lp_supply -= shares
    send(msg.sender, shares)
    return shares

@external
@view
def get_shares(provider: address) -> uint256:
    return self.lp_shares[provider]{helpers}
"""

    else:
        # Archetype 8: Dutch Auction Engine
        return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"DutchAuction_{cid}")}seller: public(address)
starting_price: public(uint256)
start_time: public(uint256)
duration: public(uint256)
is_settled: public(bool)

@deploy
def __init__(_duration: uint256, _starting_price: uint256):
    self.seller = msg.sender
    self.duration = _duration
    self.starting_price = _starting_price
    self.start_time = block.timestamp

@external
@payable
@nonreentrant
def buy():
    assert not self.is_settled, "Auction already settled"
    assert block.timestamp >= self.start_time, "Auction not started"
    assert block.timestamp <= self.start_time + self.duration, "Auction expired"
    assert msg.value >= self.starting_price, "Insufficient payment"
    self.is_settled = True
    send(self.seller, msg.value)

@external
@view
def is_active() -> bool:
    return not self.is_settled and (block.timestamp <= self.start_time + self.duration){helpers}
"""

# ==============================================================================
# 4. DIVERSE VULNERABLE VYPER CONTRACT TEMPLATES (5 CLASSES x SUB-TYPES)
# ==============================================================================
def get_vulnerable_template(vuln_type, cid):
    helpers = sample_helpers()
    sub_type = random.randint(1, 4)

    if vuln_type == "reentrancy":
        if sub_type == 1:
            # Classic Reentrancy: raw_call before state reset without @nonreentrant
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"VulnVault_{cid}")}user_balances: public(HashMap[address, uint256])

@external
@payable
def deposit():
    assert msg.value > 0, "No value sent"
    self.user_balances[msg.sender] += msg.value

@external
def withdraw_all():
    amount: uint256 = self.user_balances[msg.sender]
    assert amount > 0, "Balance is empty"
    # Flaw: Low-level raw_call executes untrusted code prior to updating balance
    raw_call(msg.sender, b"", value=amount)
    self.user_balances[msg.sender] = 0

@external
@view
def get_balance(user: address) -> uint256:
    return self.user_balances[user]{helpers}
"""
        elif sub_type == 2:
            # Reward Distributor Reentrancy
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"RewardDistributor_{cid}")}accrued_rewards: public(HashMap[address, uint256])
operator: public(address)

@deploy
def __init__():
    self.operator = msg.sender

@external
@payable
def add_rewards(user: address):
    assert msg.value > 0, "Empty rewards"
    self.accrued_rewards[user] += msg.value

@external
def claim_rewards():
    reward: uint256 = self.accrued_rewards[msg.sender]
    assert reward > 0, "Zero rewards accrued"
    # Flaw: Transfer execution before clearing reward state
    raw_call(msg.sender, b"", value=reward)
    self.accrued_rewards[msg.sender] = 0

@external
@view
def get_reward(user: address) -> uint256:
    return self.accrued_rewards[user]{helpers}
"""
        elif sub_type == 3:
            # Shared Pool Reentrancy
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"SharedYieldPool_{cid}")}deposits: public(HashMap[address, uint256])
pool_total: public(uint256)

@external
@payable
def deposit_funds():
    assert msg.value > 0, "Requires funds"
    self.deposits[msg.sender] += msg.value
    self.pool_total += msg.value

@external
def exit_pool():
    bal: uint256 = self.deposits[msg.sender]
    assert bal > 0, "No deposit in pool"
    # Flaw: External interaction before state mutation
    raw_call(msg.sender, b"", value=bal)
    self.deposits[msg.sender] = 0
    self.pool_total -= bal

@external
@view
def query_deposit(user: address) -> uint256:
    return self.deposits[user]{helpers}
"""
        else:
            # Staking Bank Reentrancy
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"StakingBank_{cid}")}stake_balance: public(HashMap[address, uint256])

@external
@payable
def stake_ether():
    assert msg.value >= 10000000000000000, "Minimum stake requirement"
    self.stake_balance[msg.sender] += msg.value

@external
def redeem_stake():
    amount: uint256 = self.stake_balance[msg.sender]
    assert amount > 0, "No stake available"
    # Flaw: Untrusted invocation hook prior to zeroing stake balance
    raw_call(msg.sender, b"", value=amount)
    self.stake_balance[msg.sender] = 0

@external
@view
def get_stake(account: address) -> uint256:
    return self.stake_balance[account]{helpers}
"""

    elif vuln_type == "access_control":
        if sub_type == 1:
            # Missing Owner Check on Sensitive Withdrawal
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"AdminTreasury_{cid}")}owner: public(address)

@deploy
def __init__():
    self.owner = msg.sender

@external
@payable
def fund_vault():
    pass

@external
def drain_to(recipient: address):
    # Flaw: Missing authorization check assert msg.sender == self.owner
    send(recipient, self.balance)

@external
@view
def get_owner() -> address:
    return self.owner{helpers}
"""
        elif sub_type == 2:
            # Unprotected Ownership Transfer
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"OwnableModule_{cid}")}admin: public(address)
paused: public(bool)

@deploy
def __init__():
    self.admin = msg.sender

@external
def set_new_admin(new_admin: address):
    # Flaw: Anyone can take over ownership
    assert new_admin != empty(address), "Invalid new admin"
    self.admin = new_admin

@external
def emergency_pause():
    assert msg.sender == self.admin, "Unauthorized caller"
    self.paused = True{helpers}
"""
        elif sub_type == 3:
            # Unprotected Token Minting Channel
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"MintableToken_{cid}")}balance_of: public(HashMap[address, uint256])
total_supply: public(uint256)
creator: public(address)

@deploy
def __init__():
    self.creator = msg.sender

@external
def mint_unrestricted(account: address, amount: uint256):
    # Flaw: Unauthenticated public access to mint state
    self.total_supply += amount
    self.balance_of[account] += amount

@external
@view
def get_balance(account: address) -> uint256:
    return self.balance_of[account]{helpers}
"""
        else:
            # Bypassable Parameter Update
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"ProtocolConfig_{cid}")}fee_rate: public(uint256)
treasury: public(address)
maintainer: public(address)

@deploy
def __init__():
    self.maintainer = msg.sender
    self.fee_rate = 50

@external
def update_fee_configuration(new_rate: uint256, new_treasury: address):
    # Flaw: Lack of guard verification on system parameters
    self.fee_rate = new_rate
    self.treasury = new_treasury

@external
@view
def get_config() -> (uint256, address):
    return (self.fee_rate, self.treasury){helpers}
"""

    elif vuln_type == "integer_overflow":
        if sub_type == 1:
            # Unsafe Addition in Loop/Accounting
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"UnsafeLedger_{cid}")}balances: public(HashMap[address, uint256])
total_staked: public(uint256)

@external
@payable
def deposit_bonus(multiplier: uint256):
    assert msg.value > 0, "No value"
    # Flaw: Explicit unchecked arithmetic wrapper causing integer wrap-around
    bonus: uint256 = unsafe_mul(msg.value, multiplier)
    self.balances[msg.sender] = unsafe_add(self.balances[msg.sender], bonus)
    self.total_staked = unsafe_add(self.total_staked, bonus)

@external
@view
def get_balance(user: address) -> uint256:
    return self.balances[user]{helpers}
"""
        elif sub_type == 2:
            # Unchecked Token Subtraction Underflow
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"UnderflowToken_{cid}")}balance_of: public(HashMap[address, uint256])

@deploy
def __init__():
    self.balance_of[msg.sender] = 1000

@external
def transfer_unchecked(to: address, amount: uint256):
    # Flaw: Using unsafe subtraction allowing underflow
    self.balance_of[msg.sender] = unsafe_sub(self.balance_of[msg.sender], amount)
    self.balance_of[to] = unsafe_add(self.balance_of[to], amount)

@external
@view
def get_balance(user: address) -> uint256:
    return self.balance_of[user]{helpers}
"""
        elif sub_type == 3:
            # Unsafe Batch Minting Arithmetic
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"BatchMinter_{cid}")}mint_count: public(uint256)

@external
def batch_mint(recipients_count: uint256, amount_per_recipient: uint256):
    # Flaw: Unsafe multiplication causes wrapping to 0, bypassing checks
    total_needed: uint256 = unsafe_mul(recipients_count, amount_per_recipient)
    self.mint_count = unsafe_add(self.mint_count, total_needed)

@external
@view
def get_mint_count() -> uint256:
    return self.mint_count{helpers}
"""
        else:
            # Reward Calculation Multiplier Underflow/Overflow
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"YieldCalculator_{cid}")}rate: public(uint256)

@deploy
def __init__():
    self.rate = 100

@external
def calculate_yield(principal: uint256, periods: uint256) -> uint256:
    # Flaw: Unsafe arithmetic chain
    compounded: uint256 = unsafe_mul(principal, unsafe_add(100, unsafe_mul(periods, self.rate)))
    return compounded // 100{helpers}
"""

    elif vuln_type == "unchecked_low_level_calls":
        if sub_type == 1:
            # Raw Call Return Value Discarded
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"SilentSender_{cid}")}owner: public(address)

@deploy
def __init__():
    self.owner = msg.sender

@external
@payable
def fund():
    pass

@external
def forward_payment(recipient: address, amount: uint256):
    assert msg.sender == self.owner, "Unauthorized"
    assert self.balance >= amount, "Insufficient balance"
    # Flaw: Low level call with revert_on_failure=False without inspecting success status
    raw_call(recipient, b"", value=amount, revert_on_failure=False)

@external
@view
def get_contract_balance() -> uint256:
    return self.balance{helpers}
"""
        elif sub_type == 2:
            # Silent Splitter Payment
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"SilentSplitter_{cid}")}payee_one: public(address)
payee_two: public(address)

@deploy
def __init__(_p1: address, _p2: address):
    self.payee_one = _p1
    self.payee_two = _p2

@external
@payable
def split_funds():
    share: uint256 = msg.value // 2
    # Flaw: Unchecked return boolean on external calls
    raw_call(self.payee_one, b"", value=share, revert_on_failure=False)
    raw_call(self.payee_two, b"", value=share, revert_on_failure=False)

@external
@view
def get_payees() -> (address, address):
    return (self.payee_one, self.payee_two){helpers}
"""
        elif sub_type == 3:
            # Batch Dispatcher ignoring return status
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"BatchDispatcher_{cid}")}admin: public(address)

@deploy
def __init__():
    self.admin = msg.sender

@external
@payable
def fund_dispatcher():
    pass

@external
def dispatch(target: address, payload: Bytes[128]):
    assert msg.sender == self.admin, "Caller is not admin"
    # Flaw: Arbitrary low-level raw_call ignoring failure
    raw_call(target, payload, revert_on_failure=False)

@external
@view
def get_admin() -> address:
    return self.admin{helpers}
"""
        else:
            # Unchecked Multi-Refund
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"RefundRouter_{cid}")}operator: public(address)

@deploy
def __init__():
    self.operator = msg.sender

@external
@payable
def deposit_reserves():
    pass

@external
def process_refund(user: address, amount: uint256):
    assert msg.sender == self.operator, "Only operator"
    # Flaw: Unchecked call leading to desynchronized accounting
    raw_call(user, b"", value=amount, revert_on_failure=False){helpers}
"""

    else: # timestamp_dependence
        if sub_type == 1:
            # Miner Manipulable Lottery / Randomness
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"BlockTimeLottery_{cid}")}manager: public(address)

@deploy
def __init__():
    self.manager = msg.sender

@external
@payable
def play_lottery() -> bool:
    assert msg.value >= 100000000000000000, "Requires 0.1 ETH"
    # Flaw: Insecure randomness derived from block.timestamp
    seed: uint256 = convert(keccak256(concat(convert(block.timestamp, bytes32), convert(msg.sender, bytes32))), uint256)
    if seed % 2 == 0:
        send(msg.sender, self.balance)
        return True
    return False

@external
@view
def get_manager() -> address:
    return self.manager{helpers}
"""
        elif sub_type == 2:
            # Strict Block Timestamp Equality
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"TimedEscrow_{cid}")}release_time: public(uint256)
beneficiary: public(address)

@deploy
@payable
def __init__(_beneficiary: address, _delay: uint256):
    self.beneficiary = _beneficiary
    self.release_time = block.timestamp + _delay

@external
def release():
    # Flaw: Strict equality on block.timestamp can be easily missed or frontrun
    assert block.timestamp == self.release_time, "Not exact release timestamp"
    send(self.beneficiary, self.balance)

@external
@view
def get_release_time() -> uint256:
    return self.release_time{helpers}
"""
        elif sub_type == 3:
            # Timestamp-based lockup bypass
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"VestingSchedule_{cid}")}vesting_cliff: public(uint256)
beneficiary: public(address)

@deploy
@payable
def __init__(_target: address, _duration: uint256):
    self.beneficiary = _target
    self.vesting_cliff = block.timestamp + _duration

@external
def withdraw_vested():
    assert msg.sender == self.beneficiary, "Not beneficiary"
    # Flaw: Short block.timestamp drift allows premature withdrawal
    assert block.timestamp >= self.vesting_cliff - 900, "Vesting cliff not reached"
    send(self.beneficiary, self.balance)

@external
@view
def get_cliff() -> uint256:
    return self.vesting_cliff{helpers}
"""
        else:
            # Timestamp Auction Expiration Flaw
            return f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

{sample_docstring(f"TimeAuction_{cid}")}auction_end: public(uint256)
highest_bidder: public(address)

@deploy
def __init__(duration: uint256):
    assert duration > 0, "Invalid duration"
    self.auction_end = block.timestamp + duration
    self.highest_bidder = msg.sender

@external
def claim_auction_reward():
    assert self.highest_bidder != empty(address), "No highest bidder"
    # Flaw: Strict timestamp equality requirement
    assert block.timestamp == self.auction_end, "Auction not exactly at deadline"
    send(self.highest_bidder, self.balance)

@external
@view
def get_auction_end() -> uint256:
    return self.auction_end{helpers}
"""

# ==============================================================================
# 5. MULTI-CONTRACT PROJECT GENERATION (FOLDER_WISE)
# ==============================================================================
def generate_multi_file_project(is_safe, vuln_type, contract_id):
    if is_safe:
        main_code = get_safe_template(contract_id)
    else:
        main_code = get_vulnerable_template(vuln_type, contract_id)

    # Vyper multi-file directory layout with main contract, interfaces, and modules
    proj_files = {
        "src/main.vy": main_code,
        "interfaces/IProtocolInterface.vy": f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

interface IProtocolInterface_{contract_id}:
    def execute_action(account: address, amount: uint256) -> bool: nonpayable
    def get_user_balance(target: address) -> uint256: view
""",
        "modules/math_extension.vy": f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

@internal
@pure
def compute_share(principal: uint256, rate: uint256) -> uint256:
    assert rate <= 10000, "Rate exceeds 100 percent"
    return (principal * rate) // 10000

@internal
@pure
def safe_min(a: uint256, b: uint256) -> uint256:
    if a < b:
        return a
    return b
"""
    }

    # Add optional helper or audit logger to diversify AST complexity and node counts
    if random.random() < 0.6:
        proj_files["helpers/context_helper.vy"] = f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

@internal
@view
def _msg_sender() -> address:
    assert msg.sender != empty(address), "Invalid caller"
    return msg.sender
"""
    if random.random() < 0.5:
        proj_files["helpers/audit_logger.vy"] = f"""# @version ^0.4.0
# SPDX-License-Identifier: MIT

event AuditLog:
    action: String[64]
    sender: address
    timestamp: uint256

@external
def log_action(action: String[64]):
    log AuditLog(action, msg.sender, block.timestamp)
"""

    return proj_files

# ==============================================================================
# 6. MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    print("=" * 80)
    print("VYPER 10,000 BALANCED DIVERSE DATASET GENERATION PIPELINE")
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

    # 1. Generate Safe Single-File Contracts (2,500)
    print("[*] Generating 2,500 Safe Single-File Vyper Contracts...")
    for _ in range(int(TARGET_SAFE_TOTAL * RATIO_FOLDERLESS)):
        code = get_safe_template(cid_counter)
        with open(safe_folderless_dir / f"safe_contract_{cid_counter}.vy", "w", encoding="utf-8") as f:
            f.write(code)
        cid_counter += 1

    # 2. Generate Safe Folder-Wise Projects (2,500)
    print("[*] Generating 2,500 Safe Folder-Wise Vyper Projects...")
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
    print("[*] Generating 2,500 Vulnerable Single-File Vyper Contracts (500 x 5 classes)...")
    for v in VULN_CLASSES:
        for _ in range(int(TARGET_VULN_PER_CLASS * RATIO_FOLDERLESS)):
            code = get_vulnerable_template(v, cid_counter)
            with open(vuln_folderless_dir / v / f"vuln_{v}_{cid_counter}.vy", "w", encoding="utf-8") as f:
                f.write(code)
            cid_counter += 1

    # 4. Generate Vulnerable Folder-Wise Projects (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Folder-Wise Vyper Projects (500 x 5 classes)...")
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

    # 5. Package into standalone dataset_vyper.zip archive
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
    print("[+] VYPER DATASET GENERATION & COMPRESSION COMPLETE!")
    print(f"    Total Contracts Created: {cid_counter - 100000}")
    print(f"    - Safe Contracts       : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise)")
    print(f"    - Vulnerable Contracts : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise across 5 classes)")
    print(f"    Folder Structure       : {OUTPUT_ROOT.resolve()}")
    print(f"    Archive Location       : {ZIP_OUTPUT.resolve()} ({zip_size_mb:.2f} MB)")
    print("=" * 80)

if __name__ == "__main__":
    main()
