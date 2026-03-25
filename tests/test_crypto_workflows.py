"""
Test 5: Crypto-Specific Workflow Tests (区块链专项)
核心问题: 交易类 skill 的链上特殊性 — finality 延迟、gas 估算、滑点、跨链状态。
"""
import os, re, json
from config import REPO_ROOT, CRYPTO_CORE_SKILLS

class CryptoWorkflowTester:
    def __init__(self):
        self.results = []

    def run(self):
        for skill in CRYPTO_CORE_SKILLS:
            skill_dir = os.path.join(REPO_ROOT, skill)
            if not os.path.isdir(skill_dir):
                continue

            py_files = [f for f in os.listdir(skill_dir) if f.endswith('.py')]
            all_content = {}
            for fname in py_files:
                with open(os.path.join(skill_dir, fname), 'r') as f:
                    all_content[fname] = f.read()

            # Run all crypto-specific checks
            self._check_tx_lifecycle(skill, all_content)
            self._check_gas_handling(skill, all_content)
            self._check_slippage_handling(skill, all_content)
            self._check_chain_id_handling(skill, all_content)
            self._check_balance_pre_check(skill, all_content)
            self._check_rate_limit_awareness(skill, all_content)
            self._check_price_staleness(skill, all_content)
            self._check_amount_precision(skill, all_content)
            self._check_address_validation(skill, all_content)

        return self.results

    def _check_tx_lifecycle(self, skill, files):
        """交易从发送到确认的完整生命周期是否被追踪"""
        combined = '\n'.join(files.values())

        # Does this skill send transactions?
        sends_tx = bool(re.search(r'(?:send_transaction|broadcast|submit|swap|transfer|order|sign.*send)', combined, re.I))
        if not sends_tx:
            return

        # Check for receipt polling / confirmation waiting
        has_receipt_check = bool(re.search(r'(?:receipt|get_transaction|wait.*confirm|poll|finality|block_number)', combined, re.I))
        has_tx_hash_return = bool(re.search(r'(?:tx_hash|transaction_hash|txHash|hash)', combined))

        if not has_receipt_check:
            self._add(skill, 'HIGH', 'NO_TX_CONFIRMATION',
                'Skill sends transactions but never checks receipt/confirmation. Agent says "done" before on-chain finality.',
                '发送交易后需要轮询 receipt 直到 confirmed/failed，再返回结果给 agent')

        if not has_tx_hash_return:
            self._add(skill, 'HIGH', 'NO_TX_HASH_RETURNED',
                'Transaction sent but tx_hash not returned to agent. Cannot verify or troubleshoot.',
                'Always return tx_hash in tool response so agent can track')

    def _check_gas_handling(self, skill, files):
        """Gas 估算和处理"""
        combined = '\n'.join(files.values())

        sends_evm_tx = bool(re.search(r'(?:send_transaction|eth_send|buildTransaction)', combined))
        if not sends_evm_tx:
            return

        has_gas_estimate = bool(re.search(r'(?:estimate_gas|gasLimit|gas_limit|gas_price|maxFeePerGas)', combined, re.I))
        has_gas_buffer = bool(re.search(r'(?:\*\s*1\.[12]|\+.*buffer|gas.*margin|gas.*multiplier)', combined))

        if not has_gas_estimate:
            self._add(skill, 'MEDIUM', 'NO_GAS_ESTIMATION',
                'Sends EVM transactions without gas estimation. May fail with out-of-gas.',
                'estimateGas before sending, add 20% buffer')

    def _check_slippage_handling(self, skill, files):
        """Swap/trade 类操作的滑点处理"""
        combined = '\n'.join(files.values())

        is_swap = bool(re.search(r'(?:swap|trade|exchange|dex|amm)', combined, re.I))
        if not is_swap:
            return

        has_slippage = bool(re.search(r'(?:slippage|slip|min_amount|minReturn|minimum.*out|amountOutMin)', combined, re.I))
        has_default_slippage = bool(re.search(r'slippage.*(?:=|default|:)\s*(?:0\.\d|1|50)', combined))

        if not has_slippage:
            self._add(skill, 'CRITICAL', 'NO_SLIPPAGE_PROTECTION',
                'Swap/trade tool has no slippage parameter. Vulnerable to sandwich attacks and MEV.',
                'Add slippage param with safe default (0.5-1%), add minAmountOut to tx')
        elif not has_default_slippage:
            self._add(skill, 'MEDIUM', 'NO_DEFAULT_SLIPPAGE',
                'Slippage parameter exists but no safe default. Small model may forget to set it.',
                'Default slippage to 0.5% or 1%')

    def _check_chain_id_handling(self, skill, files):
        """多链操作是否正确处理 chain ID"""
        combined = '\n'.join(files.values())

        is_multichain = bool(re.search(r'(?:chain_id|chainId|chain|network)', combined, re.I))
        if not is_multichain:
            return

        # Hardcoded chain IDs
        hardcoded = re.findall(r'chain_?[iI]d\s*(?:=|==|:)\s*(\d+)', combined)
        if hardcoded:
            self._add(skill, 'MEDIUM', 'HARDCODED_CHAIN_ID',
                f'Hardcoded chain IDs found: {list(set(hardcoded))}. May break on other chains.',
                'Use chain name → ID mapping, accept chain name as param')

        # Check if chain validation exists
        has_chain_validation = bool(re.search(r'(?:supported.*chain|valid.*chain|chain.*(?:not|in|supported))', combined, re.I))
        if not has_chain_validation and is_multichain:
            self._add(skill, 'MEDIUM', 'NO_CHAIN_VALIDATION',
                'Accepts chain parameter but no validation. Invalid chain → cryptic RPC error.',
                'Validate chain against supported list, return clear error')

    def _check_balance_pre_check(self, skill, files):
        """交易前是否检查余额"""
        combined = '\n'.join(files.values())

        sends_value = bool(re.search(r'(?:transfer|send|swap|withdraw|deposit)', combined, re.I))
        if not sends_value:
            return

        has_balance_check = bool(re.search(r'(?:balance|sufficient|enough|funds|insufficient)', combined, re.I))
        if not has_balance_check:
            self._add(skill, 'HIGH', 'NO_BALANCE_PRE_CHECK',
                'Executes value transfer without balance check. TX fails with unhelpful revert.',
                'Check balance before transaction, return clear "Insufficient balance: have X, need Y"')

    def _check_rate_limit_awareness(self, skill, files):
        """API 请求频率限制处理"""
        combined = '\n'.join(files.values())

        has_api_calls = bool(re.search(r'(?:proxied_get|proxied_post|requests)', combined))
        if not has_api_calls:
            return

        has_rate_handling = bool(re.search(r'(?:rate.?limit|429|too.?many|throttl|sleep|delay|backoff)', combined, re.I))
        api_call_count = len(re.findall(r'(?:proxied_get|proxied_post)', combined))

        if not has_rate_handling and api_call_count > 3:
            self._add(skill, 'MEDIUM', 'NO_RATE_LIMIT_HANDLING',
                f'Skill makes {api_call_count} API calls without rate limit handling. Burst usage → 429 errors.',
                'Add retry with backoff for 429 responses, or add request spacing')

    def _check_price_staleness(self, skill, files):
        """价格数据是否有时效性标记"""
        combined = '\n'.join(files.values())

        returns_price = bool(re.search(r'(?:price|quote|rate|ticker)', combined, re.I))
        if not returns_price:
            return

        has_timestamp = bool(re.search(r'(?:timestamp|updated_at|last_update|time|as_of)', combined))
        if not has_timestamp:
            self._add(skill, 'MEDIUM', 'NO_PRICE_TIMESTAMP',
                'Returns price data without timestamp. Agent cannot know if data is stale.',
                'Include "updated_at" or "as_of" timestamp in response')

    def _check_amount_precision(self, skill, files):
        """金额精度处理 — wei/gwei 转换, 小数精度"""
        combined = '\n'.join(files.values())

        handles_amounts = bool(re.search(r'(?:amount|value|balance|wei|gwei|lamport)', combined, re.I))
        if not handles_amounts:
            return

        has_precision_handling = bool(re.search(r'(?:10\s*\*\*|decimals|Decimal|int\(|float\(|wei.*ether|from_wei|to_wei)', combined))
        uses_float_for_money = bool(re.search(r'float\s*\(\s*(?:amount|value|balance|price)', combined))

        if uses_float_for_money:
            self._add(skill, 'HIGH', 'FLOAT_PRECISION_LOSS',
                'Uses float() for monetary values. IEEE 754 precision loss can cause wrong amounts.',
                'Use int (wei) or Decimal for monetary calculations')

        if handles_amounts and not has_precision_handling:
            self._add(skill, 'LOW', 'UNCLEAR_AMOUNT_UNITS',
                'Handles amounts without clear unit conversion. Is "1" = 1 ETH or 1 wei?',
                'Document and validate amount units. Accept human-readable, convert internally.')

    def _check_address_validation(self, skill, files):
        """地址格式验证"""
        combined = '\n'.join(files.values())

        takes_address = bool(re.search(r'(?:address|wallet|recipient|to_address|from_address)', combined, re.I))
        if not takes_address:
            return

        has_validation = bool(re.search(r'(?:is_address|checksum|0x[a-fA-F0-9]{40}|isAddress|is_valid_address|len\(.*\)\s*(?:!=|==)\s*4[02])', combined))
        if not has_validation:
            self._add(skill, 'MEDIUM', 'NO_ADDRESS_VALIDATION',
                'Accepts address parameter without format validation. Typo → funds lost or cryptic error.',
                'Validate: hex format, length (42 for EVM, 32-44 for Solana), checksum if EVM')

    def _add(self, skill, severity, issue, impact, fix=''):
        self.results.append({
            'skill': skill,
            'file': 'multiple',
            'line': 0,
            'severity': severity,
            'issue': issue,
            'impact': impact,
            'context': '',
            'fix': fix
        })


def run_test():
    tester = CryptoWorkflowTester()
    results = tester.run()

    by_skill = {}
    for r in results:
        s = r['skill']
        if s not in by_skill:
            by_skill[s] = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'total': 0}
        by_skill[s][r['severity']] += 1
        by_skill[s]['total'] += 1

    return {
        'test_name': 'Crypto-Specific Workflow Tests',
        'total_issues': len(results),
        'by_severity': {
            'CRITICAL': len([r for r in results if r['severity'] == 'CRITICAL']),
            'HIGH': len([r for r in results if r['severity'] == 'HIGH']),
            'MEDIUM': len([r for r in results if r['severity'] == 'MEDIUM']),
            'LOW': len([r for r in results if r['severity'] == 'LOW']),
        },
        'by_skill': by_skill,
        'details': results
    }

if __name__ == '__main__':
    r = run_test()
    print(json.dumps(r, indent=2, default=str))


# ---- pytest-compatible entry point ----
def test_audit_runs_without_crash():
    """Verify the audit analysis completes without exceptions."""
    result = run_test()
    assert result is not None
    assert 'test_name' in result
