# WYSIWYS Template

Use this template to translate simulation output into plain-language signing expectations.

## Required extraction

- Assets debited from user wallet
- Assets credited to user wallet
- Fee estimate in native token
- Approval changes (if any)
- Critical caveats (slippage, deadline, unresolved uncertainty)

## Plain-language format

```text
If this transaction is broadcast:
- You will spend: <amount token>
- You will receive at least: <amount token>
- Estimated network fee: <amount native token>
- Additional approval change: <description or none>
```

## Rules

- Use "at least" wording when outcome depends on slippage.
- If output token amount is uncertain, explicitly say so.
- If simulation reverted, do not provide optimistic receive amount.
- Never present simulation as guaranteed final execution.

## Revert wording template

```text
Simulation failed before execution.
- Likely failure point: <function/step>
- Observed error: <decoded message or raw revert data>
- Action: do_not_execute until issue is resolved.
```
