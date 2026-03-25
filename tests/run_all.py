#!/usr/bin/env python3
"""
Master Test Runner — runs all 5 test suites and generates unified report.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))

from test_error_handling import run_test as test_errors
from test_return_formats import run_test as test_formats
from test_skill_doc import run_test as test_docs
from test_tool_interface import run_test as test_interface
from test_crypto_workflows import run_test as test_crypto

def calc_skill_score(all_results):
    """计算每个 skill 的综合评分 (0-100)"""
    skill_issues = {}
    for suite in all_results:
        for detail in suite.get('details', []):
            s = detail['skill']
            if s not in skill_issues:
                skill_issues[s] = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
            skill_issues[s][detail['severity']] += 1

    scores = {}
    for skill, counts in skill_issues.items():
        # Penalty system: CRITICAL=-15, HIGH=-8, MEDIUM=-3, LOW=-1
        penalty = (counts['CRITICAL'] * 15 +
                   counts['HIGH'] * 8 +
                   counts['MEDIUM'] * 3 +
                   counts['LOW'] * 1)
        score = max(0, 100 - penalty)
        grades = [(90, 'A'), (75, 'B'), (60, 'C'), (40, 'D'), (0, 'F')]
        grade = next(g for threshold, g in grades if score >= threshold)
        scores[skill] = {
            'score': score,
            'grade': grade,
            'issues': counts,
            'total_issues': sum(counts.values())
        }

    return dict(sorted(scores.items(), key=lambda x: x[1]['score']))

def gen_improvement_map(all_results):
    """按 skill 生成具体改进清单 — 优先级排序"""
    fixes = {}
    for suite in all_results:
        for d in suite.get('details', []):
            s = d['skill']
            if s.startswith('_'):
                s = 'CROSS_SKILL'
            if s not in fixes:
                fixes[s] = []
            fixes[s].append({
                'severity': d['severity'],
                'issue': d['issue'],
                'impact': d['impact'],
                'fix': d.get('fix', ''),
                'file': d.get('file', ''),
                'line': d.get('line', 0),
            })

    # Sort by severity within each skill
    sev_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    for s in fixes:
        fixes[s].sort(key=lambda x: sev_order.get(x['severity'], 9))

    return fixes

def format_report(all_results, scores, fixes, doc_scores, elapsed):
    """Generate markdown report"""
    lines = []
    lines.append("# 🧪 Official-Skills 全面质量测试报告")
    lines.append(f"\n**测试时间:** {time.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**耗时:** {elapsed:.1f}s")
    lines.append(f"**核心标准:** 小模型可用性 (清晰接口 + 明确错误 + 一致格式)")
    lines.append("")

    # Executive summary
    total = sum(s.get('total_issues', 0) for s in all_results)
    crit = sum(s.get('by_severity', {}).get('CRITICAL', 0) for s in all_results)
    high = sum(s.get('by_severity', {}).get('HIGH', 0) for s in all_results)
    med = sum(s.get('by_severity', {}).get('MEDIUM', 0) for s in all_results)
    low = sum(s.get('by_severity', {}).get('LOW', 0) for s in all_results)

    lines.append("## 📊 Executive Summary")
    lines.append(f"\n| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Issues | **{total}** |")
    lines.append(f"| 🔴 CRITICAL | **{crit}** |")
    lines.append(f"| 🟠 HIGH | **{high}** |")
    lines.append(f"| 🟡 MEDIUM | **{med}** |")
    lines.append(f"| 🔵 LOW | **{low}** |")
    lines.append("")

    # Suite-level results
    lines.append("## 📋 Test Suite Results")
    lines.append(f"\n| Suite | Issues | 🔴 | 🟠 | 🟡 | 🔵 |")
    lines.append(f"|-------|--------|-----|-----|-----|-----|")
    for s in all_results:
        sv = s.get('by_severity', {})
        lines.append(f"| {s['test_name']} | {s['total_issues']} | {sv.get('CRITICAL',0)} | {sv.get('HIGH',0)} | {sv.get('MEDIUM',0)} | {sv.get('LOW',0)} |")
    lines.append("")

    # Skill scorecard
    lines.append("## 🏆 Skill Scorecard (小模型可用性评分)")
    lines.append(f"\n| Skill | Score | Grade | 🔴 | 🟠 | 🟡 | 🔵 | Total |")
    lines.append(f"|-------|-------|-------|-----|-----|-----|-----|-------|")
    for skill, data in sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True):
        c = data['issues']
        emoji = {'A':'✅','B':'🟢','C':'🟡','D':'🟠','F':'🔴'}.get(data['grade'],'❓')
        lines.append(f"| {skill} | {data['score']}/100 | {emoji} {data['grade']} | {c['CRITICAL']} | {c['HIGH']} | {c['MEDIUM']} | {c['LOW']} | {data['total_issues']} |")
    lines.append("")

    # SKILL.md doc scores
    if doc_scores:
        lines.append("## 📚 SKILL.md 文档评分")
        lines.append(f"\n| Skill | Score | Grade | Lines | Characters |")
        lines.append(f"|-------|-------|-------|-------|------------|")
        for skill, data in sorted(doc_scores.items(), key=lambda x: x[1]['pct'], reverse=True):
            emoji = {'A':'✅','B':'🟢','C':'🟡','D':'🟠','F':'🔴'}.get(data['grade'],'❓')
            lines.append(f"| {skill} | {data['score']}/{data['max_score']} ({data['pct']}%) | {emoji} {data['grade']} | {data['line_count']} | {data['char_count']} |")
        lines.append("")

    # Top issues by skill (crypto-core only)
    crypto_core = ['hyperliquid', 'coingecko', 'coinglass', '1inch', 'aave', 'debank', 'birdeye']
    lines.append("## 🔧 Crypto-Core Skills: 详细改进清单")
    for skill in crypto_core:
        if skill not in fixes:
            continue
        issues = fixes[skill]
        lines.append(f"\n### {skill} ({len(issues)} issues)")
        for i, fix in enumerate(issues[:15]):
            sev_emoji = {'CRITICAL':'🔴','HIGH':'🟠','MEDIUM':'🟡','LOW':'🔵'}.get(fix['severity'],'❓')
            loc = f"`{fix['file']}:{fix['line']}`" if fix['line'] else f"`{fix['file']}`"
            lines.append(f"\n{i+1}. {sev_emoji} **{fix['issue']}** — {loc}")
            lines.append(f"   - Impact: {fix['impact']}")
            if fix['fix']:
                lines.append(f"   - Fix: {fix['fix']}")
    lines.append("")

    # Cross-skill issues
    if 'CROSS_SKILL' in fixes:
        lines.append("## 🌐 Cross-Skill Systemic Issues")
        for fix in fixes['CROSS_SKILL']:
            sev_emoji = {'CRITICAL':'🔴','HIGH':'🟠','MEDIUM':'🟡','LOW':'🔵'}.get(fix['severity'],'❓')
            lines.append(f"\n- {sev_emoji} **{fix['issue']}**: {fix['impact']}")
            if fix['fix']:
                lines.append(f"  - Fix: {fix['fix']}")
    lines.append("")

    # Actionable next steps
    lines.append("## 🎯 一周改进优先级 (按 ROI 排序)")
    lines.append("""
| Priority | Action | Impact | Effort | Affected Skills |
|----------|--------|--------|--------|-----------------|
| P0 | 消灭 silent except:pass → 改为 raise ToolError | 小模型错误诊断能力 +300% | 4h | coinglass, birdeye, taapi, polymarket |
| P1 | 统一返回格式：success→dict, error→ToolError | 小模型解析可预测性 | 6h | 全部 12 个 |
| P2 | 给 swap/trade 加滑点保护 + 余额预检 | 防资金损失 | 4h | 1inch, hyperliquid |
| P3 | SKILL.md 加 workflow 决策树 + 错误处理段 | 小模型正确选工具 | 8h | 评分 D/F 的 skills |
| P4 | HTTP retry + timeout 标准化 | 瞬态错误自动恢复 | 3h | 10/12 skills |
| P5 | tool description 精炼 + param default 文档化 | 小模型参数准确率 | 4h | 全部 |
""")

    return '\n'.join(lines)


def main():
    print("🧪 Running all test suites...\n")
    start = time.time()

    print("[1/5] Error Handling...")
    r_errors = test_errors()
    print(f"      → {r_errors['total_issues']} issues found")

    print("[2/5] Return Formats...")
    r_formats = test_formats()
    print(f"      → {r_formats['total_issues']} issues found")

    print("[3/5] SKILL.md Docs...")
    r_docs = test_docs()
    print(f"      → {r_docs['total_issues']} issues found")

    print("[4/5] Tool Interface...")
    r_interface = test_interface()
    print(f"      → {r_interface['total_issues']} issues found")

    print("[5/5] Crypto Workflows...")
    r_crypto = test_crypto()
    print(f"      → {r_crypto['total_issues']} issues found")

    elapsed = time.time() - start
    all_results = [r_errors, r_formats, r_docs, r_interface, r_crypto]

    total = sum(r['total_issues'] for r in all_results)
    print(f"\n✅ All tests complete in {elapsed:.1f}s — {total} total issues found")

    # Calculate scores and generate report
    scores = calc_skill_score(all_results)
    fixes = gen_improvement_map(all_results)
    doc_scores = r_docs.get('scores', {})

    report = format_report(all_results, scores, fixes, doc_scores, elapsed)

    # Write report
    report_path = os.path.join(os.path.dirname(__file__), '..', 'TEST_REPORT.md')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\n📄 Report saved: {report_path}")

    # Write raw JSON for programmatic use
    json_path = os.path.join(os.path.dirname(__file__), '..', 'test_results.json')
    with open(json_path, 'w') as f:
        json.dump({
            'suites': all_results,
            'scores': scores,
            'doc_scores': doc_scores,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }, f, indent=2, default=str)
    print(f"📊 Raw data: {json_path}")

if __name__ == '__main__':
    main()
