"""
DeBank skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/debank")
    from exports import db_chain_list, db_user_total_balance
    print(db_chain_list())
    EOF

IMPORTANT NOTE on imports:
This skill's tools/ contains files named token.py, chain.py, wallet.py,
user.py — several would shadow Python stdlib modules if we naively put
tools/ on sys.path. Specifically `import token` triggers a circular
import via stdlib `tokenize`.

Strategy: load tools/utils.py manually first (so its symbols are
discoverable), then load each module by file path via importlib. This
fully bypasses sys.path-based `import` resolution and avoids stdlib
shadowing entirely.

For tools/*.py that internally do `from utils import ...`, we register
the loaded utils module under sys.modules['utils'] BEFORE loading any
other tool, so their bare `from utils import ...` resolves to our copy
rather than failing or hitting some other utils on the path.
"""
import os
import sys
import importlib.util

_TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")


def _load(modname, register_as=None):
    """Load tools/<modname>.py and optionally register in sys.modules."""
    path = os.path.join(_TOOLS_DIR, f"{modname}.py")
    spec = importlib.util.spec_from_file_location(
        register_as or f"_debank_{modname}", path
    )
    mod = importlib.util.module_from_spec(spec)
    if register_as:
        # Register first so `from <register_as> import ...` works even
        # while this module is still being executed (avoids cycles).
        sys.modules[register_as] = mod
    spec.loader.exec_module(mod)
    return mod


# Step 1: load utils first and register under bare name 'utils' so the
# subsequent tools/*.py files can do `from utils import debank_api_request`.
_utils = _load("utils", register_as="utils")
debank_api_request = _utils.debank_api_request
validate_chain_id = _utils.validate_chain_id

# Step 2: load each tool module. `_debank_*` namespace prevents stdlib
# `token` from being shadowed.
_chain = _load("chain")
_token = _load("token")
_user = _load("user")
_protocol = _load("protocol")
_wallet = _load("wallet")

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
