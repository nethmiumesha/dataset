import os
import random
import shutil
import zipfile
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION & TARGET SETUP (10,000 BALANCED DIVERSE RUST CONTRACTS)
# ==============================================================================
OUTPUT_ROOT = Path("dataset/Rust")
ZIP_OUTPUT = Path("dataset_rust.zip")

TARGET_SAFE_TOTAL = 5000
TARGET_VULN_PER_CLASS = 1000  # 1000 * 5 = 5000 Total Vulnerable
RATIO_FOLDERLESS = 0.5        # 50% Single File, 50% Multi-File Cargo Projects

VULN_CLASSES = [
    "missing_signer_check",
    "missing_owner_check",
    "integer_overflow",
    "arbitrary_cpi",
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
    """    pub fn verify_pubkey_nonzero(target: &Pubkey) -> Result<bool> {
        require!(target != &Pubkey::default(), CustomError::InvalidPubkey);
        Ok(true)
    }""",

    """    pub fn compute_protocol_fee(amount: u64, fee_bps: u64) -> Result<u64> {
        if amount == 0 || fee_bps == 0 {
            return Ok(0);
        }
        amount
            .checked_mul(fee_bps)
            .and_then(|v| v.checked_div(10000))
            .ok_or(error!(CustomError::MathOverflow))
    }""",

    """    pub fn calculate_volume_tier(volume: u64) -> u8 {
        if volume > 100_000_000_000 {
            15
        } else if volume > 10_000_000_000 {
            5
        } else {
            0
        }
    }""",

    """    pub fn get_program_version() -> &'static str {
        "v2.5.0-sealevel-production"
    }""",

    """    pub fn get_protocol_health() -> bool {
        true
    }""",

    """    pub fn check_operational_state(state_id: u32) -> Result<bool> {
        require!(state_id > 0, CustomError::InvalidStateId);
        Ok(state_id < 100)
    }""",

    """    pub fn clamp_rate(rate: u64, max_rate: u64) -> u64 {
        if rate > max_rate {
            max_rate
        } else {
            rate
        }
    }""",

    """    pub fn is_lamport_sufficient(account: &AccountInfo, min_lamports: u64) -> bool {
        account.lamports() >= min_lamports
    }"""
]

def sample_helpers():
    k = random.randint(0, 3)
    return "\n\n" + "\n\n".join(random.sample(BENIGN_HELPERS, k)) if k > 0 else ""

def sample_docstring(title):
    headers = [
        f"/// @title {title}\n/// @notice Core operational logic for decentralized Solana/Anchor program.\n",
        f"// =======================================================\n// {title.upper()}\n// =======================================================\n",
        f"/**\n * @title {title}\n * @dev Decentralized execution module with verified state management.\n */\n"
    ]
    return random.choice(headers) if random.random() < 0.7 else ""

# ==============================================================================
# 3. DIVERSE SAFE RUST / ANCHOR CONTRACT TEMPLATES (8 BALANCED ARCHETYPES)
# ==============================================================================
def get_safe_template(cid):
    archetype = random.randint(1, 8)
    helpers = sample_helpers()

    if archetype == 1:
        # Archetype 1: Secured Vault with Anchor Signer Guard & Checked Math
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("SafeVault{cid}1111111111111111111111111111111");

{sample_docstring(f"SafeVault_{cid}")}#[program]
pub mod safe_vault_{cid} {{
    use super::*;

    pub fn initialize(ctx: Context<InitializeVault>) -> Result<()> {{
        let vault = &mut ctx.accounts.vault;
        vault.authority = ctx.accounts.authority.key();
        vault.balance = 0;
        Ok(())
    }}

    pub fn deposit(ctx: Context<DepositVault>, amount: u64) -> Result<()> {{
        require!(amount > 0, CustomError::ZeroAmount);
        let vault = &mut ctx.accounts.vault;
        vault.balance = vault.balance.checked_add(amount).ok_or(CustomError::MathOverflow)?;
        Ok(())
    }}

    pub fn withdraw(ctx: Context<WithdrawVault>, amount: u64) -> Result<()> {{
        let vault = &mut ctx.accounts.vault;
        require!(vault.balance >= amount, CustomError::InsufficientFunds);
        vault.balance = vault.balance.checked_sub(amount).ok_or(CustomError::MathOverflow)?;
        **ctx.accounts.vault.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.authority.to_account_info().try_borrow_mut_lamports()? += amount;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct InitializeVault<'info> {{
    #[account(init, payer = authority, space = 8 + 32 + 8)]
    pub vault: Account<'info, VaultData>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}}

#[derive(Accounts)]
pub struct DepositVault<'info> {{
    #[account(mut, has_one = authority)]
    pub vault: Account<'info, VaultData>,
    pub authority: Signer<'info>,
}}

#[derive(Accounts)]
pub struct WithdrawVault<'info> {{
    #[account(mut, has_one = authority)]
    pub vault: Account<'info, VaultData>,
    #[account(mut)]
    pub authority: Signer<'info>,
}}

#[account]
pub struct VaultData {{
    pub authority: Pubkey,
    pub balance: u64,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Amount must be greater than zero")]
    ZeroAmount,
    #[msg("Math calculation overflowed")]
    MathOverflow,
    #[msg("Insufficient vault funds")]
    InsufficientFunds,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

    elif archetype == 2:
        # Archetype 2: Staking Pool with Strict Verification
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("SafeStk{cid}11111111111111111111111111111111");

{sample_docstring(f"StakingPool_{cid}")}#[program]
pub mod staking_pool_{cid} {{
    use super::*;

    pub fn stake(ctx: Context<StakeContext>, amount: u64) -> Result<()> {{
        require!(amount > 0, CustomError::ZeroAmount);
        let user_stake = &mut ctx.accounts.user_stake;
        user_stake.staked_amount = user_stake.staked_amount.checked_add(amount).ok_or(CustomError::MathOverflow)?;
        Ok(())
    }}

    pub fn unstake(ctx: Context<UnstakeContext>, amount: u64) -> Result<()> {{
        let user_stake = &mut ctx.accounts.user_stake;
        require!(user_stake.staked_amount >= amount, CustomError::InsufficientFunds);
        user_stake.staked_amount = user_stake.staked_amount.checked_sub(amount).ok_or(CustomError::MathOverflow)?;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct StakeContext<'info> {{
    #[account(mut, has_one = owner)]
    pub user_stake: Account<'info, StakeAccount>,
    pub owner: Signer<'info>,
}}

#[derive(Accounts)]
pub struct UnstakeContext<'info> {{
    #[account(mut, has_one = owner)]
    pub user_stake: Account<'info, StakeAccount>,
    pub owner: Signer<'info>,
}}

#[account]
pub struct StakeAccount {{
    pub owner: Pubkey,
    pub staked_amount: u64,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Zero amount requested")]
    ZeroAmount,
    #[msg("Math calculation overflowed")]
    MathOverflow,
    #[msg("Insufficient staked balance")]
    InsufficientFunds,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

    elif archetype == 3:
        # Archetype 3: Escrow Settlement Contract
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("SafeEsc{cid}11111111111111111111111111111111");

{sample_docstring(f"EscrowAgreement_{cid}")}#[program]
pub mod escrow_{cid} {{
    use super::*;

    pub fn release_escrow(ctx: Context<ReleaseEscrow>) -> Result<()> {{
        let escrow = &mut ctx.accounts.escrow;
        require!(!escrow.is_finalized, CustomError::AlreadyFinalized);
        escrow.is_finalized = true;
        
        let amount = escrow.amount;
        **ctx.accounts.escrow.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.seller.to_account_info().try_borrow_mut_lamports()? += amount;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct ReleaseEscrow<'info> {{
    #[account(mut, has_one = buyer, has_one = seller)]
    pub escrow: Account<'info, EscrowState>,
    pub buyer: Signer<'info>,
    /// CHECK: Seller address is verified by has_one constraint
    #[account(mut)]
    pub seller: AccountInfo<'info>,
}}

#[account]
pub struct EscrowState {{
    pub buyer: Pubkey,
    pub seller: Pubkey,
    pub amount: u64,
    pub is_finalized: bool,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Escrow agreement already finalized")]
    AlreadyFinalized,
    #[msg("Math calculation overflowed")]
    MathOverflow,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

    elif archetype == 4:
        # Archetype 4: Treasury Governor with Role Verification
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("SafeGov{cid}11111111111111111111111111111111");

{sample_docstring(f"TreasuryGovernor_{cid}")}#[program]
pub mod treasury_governor_{cid} {{
    use super::*;

    pub fn disburse(ctx: Context<DisburseFunds>, amount: u64) -> Result<()> {{
        let treasury = &mut ctx.accounts.treasury;
        require!(treasury.balance >= amount, CustomError::InsufficientFunds);
        treasury.balance = treasury.balance.checked_sub(amount).ok_or(CustomError::MathOverflow)?;
        treasury.disbursement_count = treasury.disbursement_count.checked_add(1).ok_or(CustomError::MathOverflow)?;

        **ctx.accounts.treasury.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.recipient.to_account_info().try_borrow_mut_lamports()? += amount;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct DisburseFunds<'info> {{
    #[account(mut, has_one = governor)]
    pub treasury: Account<'info, TreasuryState>,
    pub governor: Signer<'info>,
    /// CHECK: Recipient pubkey verified
    #[account(mut)]
    pub recipient: AccountInfo<'info>,
}}

#[account]
pub struct TreasuryState {{
    pub governor: Pubkey,
    pub balance: u64,
    pub disbursement_count: u64,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Insufficient treasury balance")]
    InsufficientFunds,
    #[msg("Math calculation overflowed")]
    MathOverflow,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

    elif archetype == 5:
        # Archetype 5: Verified Cross-Program Invocation (Safe CPI)
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;
use anchor_spl::token::{{self, Token, TokenAccount, Transfer}};

declare_id!("SafeCpi{cid}11111111111111111111111111111111");

{sample_docstring(f"SafeTransferModule_{cid}")}#[program]
pub mod safe_transfer_{cid} {{
    use super::*;

    pub fn transfer_tokens(ctx: Context<TransferTokensContext>, amount: u64) -> Result<()> {{
        let cpi_accounts = Transfer {{
            from: ctx.accounts.from.to_account_info(),
            to: ctx.accounts.to.to_account_info(),
            authority: ctx.accounts.authority.to_account_info(),
        }};
        // Safe: Token program explicitly constrained to official SPL Token Program
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
        token::transfer(cpi_ctx, amount)?;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct TransferTokensContext<'info> {{
    #[account(mut)]
    pub from: Account<'info, TokenAccount>,
    #[account(mut)]
    pub to: Account<'info, TokenAccount>,
    pub authority: Signer<'info>,
    pub token_program: Program<'info, Token>,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Math calculation overflowed")]
    MathOverflow,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

    elif archetype == 6:
        # Archetype 6: Multi-Signature Execution Channel
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("SafeMsg{cid}11111111111111111111111111111111");

{sample_docstring(f"MultiSigExecutor_{cid}")}#[program]
pub mod multisig_{cid} {{
    use super::*;

    pub fn confirm_and_execute(ctx: Context<MultiSigContext>, amount: u64) -> Result<()> {{
        let ms = &mut ctx.accounts.multisig;
        require!(ctx.accounts.signer_a.key() == ms.signer_one, CustomError::Unauthorized);
        require!(ctx.accounts.signer_b.key() == ms.signer_two, CustomError::Unauthorized);
        ms.execution_count = ms.execution_count.checked_add(1).ok_or(CustomError::MathOverflow)?;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct MultiSigContext<'info> {{
    #[account(mut)]
    pub multisig: Account<'info, MultiSigState>,
    pub signer_a: Signer<'info>,
    pub signer_b: Signer<'info>,
}}

#[account]
pub struct MultiSigState {{
    pub signer_one: Pubkey,
    pub signer_two: Pubkey,
    pub execution_count: u64,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Unauthorized signer access")]
    Unauthorized,
    #[msg("Math calculation overflowed")]
    MathOverflow,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

    elif archetype == 7:
        # Archetype 7: Liquidity Pool
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("SafeLiq{cid}11111111111111111111111111111111");

{sample_docstring(f"LiquidityPool_{cid}")}#[program]
pub mod liquidity_pool_{cid} {{
    use super::*;

    pub fn add_liquidity(ctx: Context<AddLiquidityContext>, amount: u64) -> Result<()> {{
        require!(amount > 0, CustomError::ZeroAmount);
        let pool = &mut ctx.accounts.pool;
        pool.total_lp = pool.total_lp.checked_add(amount).ok_or(CustomError::MathOverflow)?;
        let provider = &mut ctx.accounts.provider_shares;
        provider.shares = provider.shares.checked_add(amount).ok_or(CustomError::MathOverflow)?;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct AddLiquidityContext<'info> {{
    #[account(mut)]
    pub pool: Account<'info, PoolState>,
    #[account(mut, has_one = owner)]
    pub provider_shares: Account<'info, ShareAccount>,
    pub owner: Signer<'info>,
}}

#[account]
pub struct PoolState {{
    pub total_lp: u64,
}}

#[account]
pub struct ShareAccount {{
    pub owner: Pubkey,
    pub shares: u64,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Zero amount cannot be added")]
    ZeroAmount,
    #[msg("Math calculation overflowed")]
    MathOverflow,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

    else:
        # Archetype 8: Secure Timed Vesting (Proper boundary verification)
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("SafeVst{cid}11111111111111111111111111111111");

{sample_docstring(f"TimedVesting_{cid}")}#[program]
pub mod timed_vesting_{cid} {{
    use super::*;

    pub fn claim_vested(ctx: Context<ClaimVestedContext>) -> Result<()> {{
        let schedule = &mut ctx.accounts.vesting_schedule;
        let clock = Clock::get()?;
        require!(clock.unix_timestamp >= schedule.cliff_timestamp, CustomError::CliffNotReached);
        require!(!schedule.is_claimed, CustomError::AlreadyFinalized);
        schedule.is_claimed = true;

        let amount = schedule.amount;
        **ctx.accounts.vesting_schedule.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.beneficiary.to_account_info().try_borrow_mut_lamports()? += amount;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct ClaimVestedContext<'info> {{
    #[account(mut, has_one = beneficiary)]
    pub vesting_schedule: Account<'info, VestingSchedule>,
    #[account(mut)]
    pub beneficiary: Signer<'info>,
}}

#[account]
pub struct VestingSchedule {{
    pub beneficiary: Pubkey,
    pub cliff_timestamp: i64,
    pub amount: u64,
    pub is_claimed: bool,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Vesting cliff deadline has not been reached yet")]
    CliffNotReached,
    #[msg("Vested tokens already claimed")]
    AlreadyFinalized,
    #[msg("Invalid pubkey provided")]
    InvalidPubkey,
    #[msg("Invalid state ID")]
    InvalidStateId,
}}
"""

# ==============================================================================
# 4. DIVERSE VULNERABLE RUST CONTRACT TEMPLATES (5 CLASSES x SUB-TYPES)
# ==============================================================================
def get_vulnerable_template(vuln_type, cid):
    helpers = sample_helpers()
    sub_type = random.randint(1, 4)

    if vuln_type == "missing_signer_check":
        # Flaw: Authority passed as AccountInfo instead of Signer, or missing is_signer
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("VulnSig{cid}11111111111111111111111111111111");

{sample_docstring(f"VulnSignerVault_{cid}")}#[program]
pub mod vuln_signer_{cid} {{
    use super::*;

    pub fn withdraw(ctx: Context<WithdrawUnchecked>, amount: u64) -> Result<()> {{
        let vault = &mut ctx.accounts.vault;
        // Flaw: authority is an unverified AccountInfo, anyone can impersonate the owner!
        vault.balance = vault.balance.saturating_sub(amount);
        **ctx.accounts.vault.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.recipient.to_account_info().try_borrow_mut_lamports()? += amount;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct WithdrawUnchecked<'info> {{
    #[account(mut)]
    pub vault: Account<'info, VaultData>,
    /// CHECK: Missing is_signer check! Vulnerable to caller spoofing!
    pub authority: AccountInfo<'info>,
    /// CHECK: Recipient account
    #[account(mut)]
    pub recipient: AccountInfo<'info>,
}}

#[account]
pub struct VaultData {{
    pub authority: Pubkey,
    pub balance: u64,
}}
"""

    elif vuln_type == "missing_owner_check":
        # Flaw: Account data type confusion or missing program owner validation
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("VulnOwn{cid}11111111111111111111111111111111");

{sample_docstring(f"VulnOwnerCheck_{cid}")}#[program]
pub mod vuln_owner_{cid} {{
    use super::*;

    pub fn update_governance_data(ctx: Context<UpdateData>, new_admin: Pubkey) -> Result<()> {{
        // Flaw: target_state passed as unchecked AccountInfo without checking target_state.owner == program_id
        let mut data = ctx.accounts.target_state.try_borrow_mut_data()?;
        data[0..32].copy_from_slice(new_admin.as_ref());
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct UpdateData<'info> {{
    /// CHECK: Missing owner check! Malicious actor can pass account owned by external program
    #[account(mut)]
    pub target_state: AccountInfo<'info>,
    pub caller: Signer<'info>,
}}
"""

    elif vuln_type == "integer_overflow":
        # Flaw: Raw arithmetic without checked/saturating helpers, causing wrap-around
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("VulnOvf{cid}11111111111111111111111111111111");

{sample_docstring(f"VulnArithmetic_{cid}")}#[program]
pub mod vuln_overflow_{cid} {{
    use super::*;

    pub fn batch_mint_bonus(ctx: Context<MintContext>, multiplier: u64, base_units: u64) -> Result<()> {{
        let pool = &mut ctx.accounts.pool;
        // Flaw: Unchecked multiplication and addition causing integer wrap in release mode
        let bonus = multiplier * base_units;
        pool.total_minted = pool.total_minted + bonus;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct MintContext<'info> {{
    #[account(mut)]
    pub pool: Account<'info, PoolData>,
    pub authority: Signer<'info>,
}}

#[account]
pub struct PoolData {{
    pub total_minted: u64,
}}
"""

    elif vuln_type == "arbitrary_cpi":
        # Flaw: Arbitrary program invocation without verifying program ID
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;
use solana_program::program::invoke;

declare_id!("VulnCpi{cid}11111111111111111111111111111111");

{sample_docstring(f"VulnArbitraryCpi_{cid}")}#[program]
pub mod vuln_cpi_{cid} {{
    use super::*;

    pub fn dispatch_action(ctx: Context<DispatchContext>, instruction_data: Vec<u8>) -> Result<()> {{
        let ix = solana_program::instruction::Instruction {{
            // Flaw: target_program is completely arbitrary without checking it matches official target ID!
            program_id: *ctx.accounts.target_program.key,
            accounts: vec![],
            data: instruction_data,
        }};
        invoke(&ix, &[ctx.accounts.target_program.clone()])?;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct DispatchContext<'info> {{
    /// CHECK: Arbitrary program ID unverified
    pub target_program: AccountInfo<'info>,
    pub caller: Signer<'info>,
}}
"""

    else: # timestamp_dependence
        # Flaw: Insecure randomness or strict equality on Clock unix_timestamp
        return f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

declare_id!("VulnTim{cid}11111111111111111111111111111111");

{sample_docstring(f"VulnTimestamp_{cid}")}#[program]
pub mod vuln_timestamp_{cid} {{
    use super::*;

    pub fn claim_lottery_prize(ctx: Context<LotteryContext>) -> Result<()> {{
        let clock = Clock::get()?;
        // Flaw: Strict timestamp equality on miner-influencable block time
        require!(clock.unix_timestamp == ctx.accounts.game.target_timestamp, CustomError::WrongTimestamp);
        
        **ctx.accounts.game.to_account_info().try_borrow_mut_lamports()? -= 1_000_000_000;
        **ctx.accounts.winner.to_account_info().try_borrow_mut_lamports()? += 1_000_000_000;
        Ok(())
    }}
{helpers}
}}

#[derive(Accounts)]
pub struct LotteryContext<'info> {{
    #[account(mut)]
    pub game: Account<'info, GameState>,
    #[account(mut)]
    pub winner: Signer<'info>,
}}

#[account]
pub struct GameState {{
    pub target_timestamp: i64,
}}

#[error_code]
pub enum CustomError {{
    #[msg("Clock unix timestamp is not exactly equal to target timestamp")]
    WrongTimestamp,
}}
"""

# ==============================================================================
# 5. MULTI-FILE PROJECT GENERATION (CARGO CRATE LAYOUT)
# ==============================================================================
def generate_multi_file_project(is_safe, vuln_type, contract_id):
    if is_safe:
        main_code = get_safe_template(contract_id)
    else:
        main_code = get_vulnerable_template(vuln_type, contract_id)

    proj_files = {
        "Cargo.toml": f"""[package]
name = "solana_project_{contract_id}"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "lib"]
name = "solana_project_{contract_id}"

[dependencies]
anchor-lang = "0.29.0"
anchor-spl = "0.29.0"
solana-program = "1.17.0"
""",
        "src/lib.rs": main_code,
        "src/state.rs": f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

#[account]
pub struct GlobalConfigState_{contract_id} {{
    pub admin: Pubkey,
    pub is_paused: bool,
    pub fee_bps: u64,
}}

impl GlobalConfigState_{contract_id} {{
    pub const LEN: usize = 8 + 32 + 1 + 8;
}}
""",
        "src/utils.rs": f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

pub fn safe_calc_share(principal: u64, bps: u64) -> Option<u64> {{
    if bps > 10000 {{
        return None;
    }}
    principal.checked_mul(bps)?.checked_div(10000)
}}
"""
    }

    if random.random() < 0.6:
        proj_files["src/errors.rs"] = f"""// SPDX-License-Identifier: MIT
use anchor_lang::prelude::*;

#[error_code]
pub enum ModuleCustomErrors_{contract_id} {{
    #[msg("Operation rejected: System under maintenance")]
    SystemPaused,
    #[msg("Unauthorized invocation context")]
    AccessDenied,
}}
"""

    return proj_files

# ==============================================================================
# 6. MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    print("=" * 80)
    print("RUST (SOLANA/ANCHOR) 10,000 BALANCED DIVERSE DATASET GENERATION PIPELINE")
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
    print("[*] Generating 2,500 Safe Single-File Rust Programs...")
    for _ in range(int(TARGET_SAFE_TOTAL * RATIO_FOLDERLESS)):
        code = get_safe_template(cid_counter)
        with open(safe_folderless_dir / f"safe_program_{cid_counter}.rs", "w", encoding="utf-8") as f:
            f.write(code)
        cid_counter += 1

    # 2. Generate Safe Folder-Wise Cargo Projects (2,500)
    print("[*] Generating 2,500 Safe Folder-Wise Rust Projects...")
    for _ in range(int(TARGET_SAFE_TOTAL * (1 - RATIO_FOLDERLESS))):
        proj_dir = safe_folderwise_dir / f"safe_project_{cid_counter}"
        files = generate_multi_file_project(is_safe=True, vuln_type=None, contract_id=cid_counter)
        for rel_path, content in files.items():
            full_path = proj_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        cid_counter += 1

    # 3. Generate Vulnerable Single-File Programs (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Single-File Rust Programs (500 x 5 classes)...")
    for v in VULN_CLASSES:
        for _ in range(int(TARGET_VULN_PER_CLASS * RATIO_FOLDERLESS)):
            code = get_vulnerable_template(v, cid_counter)
            with open(vuln_folderless_dir / v / f"vuln_{v}_{cid_counter}.rs", "w", encoding="utf-8") as f:
                f.write(code)
            cid_counter += 1

    # 4. Generate Vulnerable Folder-Wise Cargo Projects (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Folder-Wise Rust Projects (500 x 5 classes)...")
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

    # 5. Package into standalone dataset_rust.zip archive
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
    print("[+] RUST DATASET GENERATION & COMPRESSION COMPLETE!")
    print(f"    Total Programs Created : {cid_counter - 100000}")
    print(f"    - Safe Programs        : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise)")
    print(f"    - Vulnerable Programs  : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise across 5 classes)")
    print(f"    Folder Structure       : {OUTPUT_ROOT.resolve()}")
    print(f"    Archive Location       : {ZIP_OUTPUT.resolve()} ({zip_size_mb:.2f} MB)")
    print("=" * 80)

if __name__ == "__main__":
    main()
