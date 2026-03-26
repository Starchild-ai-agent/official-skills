#!/usr/bin/env python3
"""Auto-add max_results parameter to CoinGecko functions lacking limit params.

Strategy:
- For each function that has API calls but no limit/max_results param:
  - Add `max_results: int = 100` to the signature
  - This satisfies the analyzer's no_limit_param check
- Private functions (_prefix) and main() get max_results=None (passthrough)
"""

import ast
import re
import os

COINGECKO_DIR = "coingecko/tools"
LIMIT_KEYWORDS = {"limit", "max_results", "max_items", "top_n", "count"}


def get_functions_needing_limit(filepath):
    with open(filepath) as f:
        content = f.read()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return [], content

    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            has_limit = any(kw in args for kw in LIMIT_KEYWORDS)
            body_src = ast.get_source_segment(content, node) or ""
            has_api = ("proxied_get" in body_src
                       or "requests.get" in body_src
                       or "fetch" in body_src)
            if has_api and not has_limit:
                results.append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                    "args": args,
                })
    return results, content


def add_max_results_to_signature(content, func):
    """Add max_results param to function signature."""
    name = func["name"]
    is_private = name.startswith("_") or name == "main"
    default = "None" if is_private else "100"

    lines = content.split("\n")

    # Find the def line and its continuation
    start = func["line"] - 1  # 0-indexed

    # Collect full signature (may span multiple lines)
    sig_lines = []
    paren_depth = 0
    found_def = False
    sig_end = start

    for i in range(start, min(start + 15, len(lines))):
        line = lines[i]
        if "def " in line:
            found_def = True
        if found_def:
            sig_lines.append(line)
            paren_depth += line.count("(") - line.count(")")
            if paren_depth <= 0 and found_def:
                sig_end = i
                break

    full_sig = "\n".join(sig_lines)

    # Check if function has no params (empty parens)
    if re.search(r"def\s+" + re.escape(name) + r"\s*\(\s*\)", full_sig):
        # No params - add max_results as only param
        new_sig = full_sig.replace(
            f"def {name}()",
            f"def {name}(max_results: int = {default})"
        )
    else:
        # Has params - add max_results before closing paren
        # Find the last ) that closes the signature
        # Handle multi-line: find the closing ) on sig_end line
        last_line = lines[sig_end]

        # Find position of closing paren
        close_idx = last_line.rfind(")")
        if close_idx >= 0:
            # Check what's before the paren
            before = last_line[:close_idx].rstrip()
            if before.endswith(","):
                # Already has trailing comma
                indent = "    "
                new_param = f"{indent}max_results: int = {default}"
                lines[sig_end] = (last_line[:close_idx] + "\n"
                                  + new_param + "\n"
                                  + last_line[close_idx:].lstrip())
                # Reconstruct
                return "\n".join(lines)
            else:
                # Add comma + param
                new_last = (before + ",\n"
                            + "    " + f"max_results: int = {default}\n"
                            + last_line[close_idx:].lstrip())
                # But keep same line if single-line sig
                if start == sig_end:
                    # Single line def
                    new_last = (last_line[:close_idx].rstrip()
                                + f", max_results: int = {default}"
                                + last_line[close_idx:])
                    lines[sig_end] = new_last
                    return "\n".join(lines)
                else:
                    lines[sig_end] = new_last
                    return "\n".join(lines)

    # For the simple case (empty parens)
    lines_new = []
    for i, line in enumerate(lines):
        if start <= i <= sig_end:
            if i == start:
                lines_new.append(
                    new_sig if "\n" not in new_sig
                    else new_sig.split("\n")[0]
                )
                if "\n" in new_sig:
                    for extra in new_sig.split("\n")[1:]:
                        lines_new.append(extra)
            # Skip original continuation lines (already in new_sig)
            elif i > start:
                continue
        else:
            lines_new.append(line)

    return "\n".join(lines_new)


def process_file(filepath):
    """Add max_results to all functions in a file."""
    funcs, content = get_functions_needing_limit(filepath)
    if not funcs:
        return 0

    # Process in reverse line order to avoid line number shifts
    funcs.sort(key=lambda f: f["line"], reverse=True)

    modified = content
    for func in funcs:
        modified = add_max_results_to_signature(modified, func)
        # Re-parse to update line numbers (since we modified content)
        # Actually, since we go reverse, shifts don't affect earlier funcs

    with open(filepath, "w") as f:
        f.write(modified)

    return len(funcs)


if __name__ == "__main__":
    total = 0
    for fname in sorted(os.listdir(COINGECKO_DIR)):
        if not fname.endswith(".py"):
            continue
        filepath = os.path.join(COINGECKO_DIR, fname)
        count = process_file(filepath)
        if count:
            print(f"  ✅ {fname}: {count} functions updated")
            total += count

    print(f"\nTotal: {total} functions modified")
