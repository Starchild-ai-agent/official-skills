"""
DeBank skill exports — tool names match SKILL.md frontmatter.

Usage in task scripts:
    from core.skill_tools import debank
    balance = debank.db_user_total_balance(user_addr="0x...")
    tokens = debank.db_user_all_token_list(user_addr="0x...")
    chains = debank.db_chain_list()
"""
from utils import debank_api_request, validate_chain_id
import chain as _chain
import token as _token
import user as _user
import protocol as _protocol
import wallet as _wallet

# --- Chain ---
def db_chain_list():
    """Get list of supported chains."""
    return _chain.get_chain_list()

def db_chain(chain_id):
    """Get details of a specific chain."""
    return _chain.get_chain(chain_id=chain_id)

def db_gas_market(chain_id):
    """Get gas prices for a chain."""
    return _chain.get_gas_market(chain_id=chain_id)

# --- Token ---
def db_token(chain_id, token_id):
    """Get token details."""
    return _token.get_token(chain_id=chain_id, token_id=token_id)

def db_token_history_price(chain_id, token_id, start_time, end_time=None):
    """Get token historical price."""
    return _token.get_token_history_price(chain_id=chain_id, token_id=token_id, start_time=start_time, end_time=end_time)

def db_token_list_by_ids(chain_id, token_ids):
    """Batch fetch multiple tokens on a chain."""
    return _token.get_token_list_by_ids(chain_id=chain_id, token_ids=token_ids)

def db_token_top_holders(chain_id, token_id, start=0):
    """Get top holders of a token."""
    return _token.get_token_top_holders(chain_id=chain_id, token_id=token_id, start=start)

# --- User ---
def db_user_total_balance(user_addr):
    return _user.get_user_total_balance(user_addr=user_addr)

def db_user_token_list(user_addr, chain_id, is_all=None):
    return _user.get_user_token_list(user_addr=user_addr, chain_id=chain_id, is_all=is_all)

def db_user_all_token_list(user_addr, is_all=None):
    return _user.get_user_all_token_list(user_addr=user_addr, is_all=is_all)

def db_user_history_list(user_addr, chain_id, start_time=None, page_count=None):
    return _user.get_user_history_list(user_addr=user_addr, chain_id=chain_id, start_time=start_time, page_count=page_count)

def db_user_all_history_list(user_addr, start_time=None, page_count=None):
    return _user.get_user_all_history_list(user_addr=user_addr, start_time=start_time, page_count=page_count)

def db_user_simple_protocol_list(user_addr, chain_id):
    return _user.get_user_simple_protocol_list(user_addr=user_addr, chain_id=chain_id)

def db_user_all_simple_protocol_list(user_addr):
    return _user.get_user_all_simple_protocol_list(user_addr=user_addr)

def db_user_complex_protocol_list(user_addr, chain_id):
    return _user.get_user_complex_protocol_list(user_addr=user_addr, chain_id=chain_id)

def db_user_all_complex_protocol_list(user_addr):
    return _user.get_user_all_complex_protocol_list(user_addr=user_addr)

def db_user_complex_app_list(user_addr):
    return _user.get_user_complex_app_list(user_addr=user_addr)

def db_user_nft_list(user_addr, chain_id, is_all=None):
    return _user.get_user_nft_list(user_addr=user_addr, chain_id=chain_id, is_all=is_all)

def db_user_all_nft_list(user_addr, is_all=None):
    return _user.get_user_all_nft_list(user_addr=user_addr, is_all=is_all)

def db_user_chain_balance(user_addr, chain_id):
    return _user.get_user_chain_balance(user_addr=user_addr, chain_id=chain_id)

def db_user_token(user_addr, chain_id, token_id):
    return _user.get_user_token(user_addr=user_addr, chain_id=chain_id, token_id=token_id)

def db_user_protocol(user_addr, protocol_id):
    return _user.get_user_protocol(user_addr=user_addr, protocol_id=protocol_id)

def db_user_used_chain_list(user_addr):
    return _user.get_user_used_chain_list(user_addr=user_addr)

def db_user_token_authorized_list(user_addr, chain_id):
    return _user.get_user_token_authorized_list(user_addr=user_addr, chain_id=chain_id)

def db_user_nft_authorized_list(user_addr, chain_id):
    return _user.get_user_nft_authorized_list(user_addr=user_addr, chain_id=chain_id)

def db_user_chain_net_curve(user_addr, chain_id):
    return _user.get_user_chain_net_curve(user_addr=user_addr, chain_id=chain_id)

def db_user_total_net_curve(user_addr):
    return _user.get_user_total_net_curve(user_addr=user_addr)

# --- Protocol ---
def db_protocol(protocol_id):
    return _protocol.get_protocol(protocol_id=protocol_id)

def db_protocol_list(chain_id):
    return _protocol.get_protocol_list(chain_id=chain_id)

def db_protocol_all_list():
    return _protocol.get_protocol_all_list()

def db_app_protocol_list():
    return _protocol.get_app_protocol_list()

def db_pool(protocol_id, chain_id, pool_id):
    return _protocol.get_pool(protocol_id=protocol_id, chain_id=chain_id, pool_id=pool_id)

# --- Wallet / Tx ---
def db_pre_exec_tx(user_addr, chain_id, tx):
    return _wallet.pre_exec_tx(user_addr=user_addr, chain_id=chain_id, tx=tx)

def db_explain_tx(user_addr, chain_id, tx):
    return _wallet.explain_tx(user_addr=user_addr, chain_id=chain_id, tx=tx)
