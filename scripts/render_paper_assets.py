#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
PAPER = PROJECT / "paper"


def esc(value: str) -> str:
    return value.replace("_", r"\_").replace("%", r"\%")


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}"


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def write_table(path: str, headers: list[str], rows: list[list[str]], caption: str) -> None:
    alignment = "l" + "r" * (len(headers) - 1)
    lines = [
        r"\begin{table}[t]", r"\centering", r"\small",
        rf"\caption{{{caption}}}", rf"\begin{{tabular}}{{{alignment}}}",
        r"\toprule", " & ".join(headers) + r" \\", r"\midrule",
    ]
    lines.extend(" & ".join(row) + r" \\" for row in rows)
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    (PAPER / path).write_text("\n".join(lines) + "\n")


def main() -> None:
    development = json.loads((PROJECT / "results/development/gate_summary.json").read_text())
    development_method = json.loads(
        (PROJECT / "results/development_v2/analysis/summary.json").read_text()
    )
    confirmation = json.loads((PROJECT / "results/confirmation/final/summary.json").read_text())
    labels = [
        json.loads(line)
        for line in (PROJECT / "results/confirmation/final/labels.jsonl").read_text().splitlines()
        if line.strip()
    ]
    evaluated = [
        json.loads(line)
        for line in (PROJECT / "results/confirmation/final/evaluated.jsonl").read_text().splitlines()
        if line.strip()
    ]
    method_name = confirmation["primary_method"]
    comparator_name = confirmation["frozen_primary_comparator"]
    method = confirmation["arms"][method_name]
    comparator = confirmation["arms"][comparator_name]
    method_rows = [row for row in evaluated if row["arm"] == method_name]
    causal_method = [row for row in method_rows if row["conflict_class"] != "no_conflict"]
    by_environment = defaultdict(list)
    for row in causal_method:
        by_environment[row["environment"]].append(row)
    rely = [row for row in causal_method if row["conflict_class"] == "rely_gap"]
    valid_sources = sum(
        row["valid"] and row["conflict_class"] == "no_conflict" for row in labels
    )
    inference = confirmation["primary_inference"]
    ci = inference["bootstrap_95_percent_ci"]
    pvalue = inference["paired_task_sign_randomization_p_two_sided"]
    macros = {
        "DevelopmentIncidentCount": development_method["all"]["n"],
        "DevelopmentCausalCount": development_method["causal_conflicts"]["n"],
        "DevelopmentMethodRate": pct(development["causal_constrained_success"]),
        "DevelopmentComparatorRate": pct(development["comparator_causal_constrained_success"]),
        "DevelopmentGain": pct(development["gain"]),
        "DevelopmentControlRate": pct(
            development["all_development_arms"]["cgba"]["control_native_success"]
        ),
        "DevelopmentRollbackRate": pct(
            development["all_development_arms"]["whole_chain_rollback"]["causal_native_success"]
        ),
        "ConfirmationRosterCount": json.loads(
            (PROJECT / "data/confirmation/roster.json").read_text()
        )["task_count"],
        "SuccessfulSourceCount": valid_sources,
        "ValidCausalCount": confirmation["validity"]["valid_causal_conflicts"],
        "ValidControlCount": confirmation["validity"]["valid_controls"],
        "PrimaryMethodRate": pct(method["causal_conflicts"]["constrained_success_rate"]),
        "PrimaryComparatorRate": pct(
            comparator["causal_conflicts"]["constrained_success_rate"]
        ),
        "PrimaryGain": pct(confirmation["gain_over_frozen_comparator"]),
        "PrimaryCILow": pct(ci[0]),
        "PrimaryCIHigh": pct(ci[1]),
        "PrimaryP": f"{pvalue:.5f}",
        "ControlLoss": pct(confirmation["healthy_control_loss"]),
        "ConfirmationStatus": esc(confirmation["status"].replace("_", " ")),
        "MeanAdapterActions": f"{mean([row['proposed_adapter_actions'] for row in causal_method]):.2f}",
        "MaxAdapterActions": max(row["proposed_adapter_actions"] for row in causal_method),
        "MeanRelyAdapterActions": f"{mean([row['proposed_adapter_actions'] for row in rely]):.2f}",
    }
    (PAPER / "results_macros.tex").write_text("".join(
        rf"\newcommand{{\{key}}}{{{value}}}" + "\n" for key, value in macros.items()
    ))

    arm_labels = {
        "cgba": "CGBAS", "no_repair": "No repair",
        "pairwise_contract": "Pairwise contract", "whole_chain_rollback": "Whole-chain rollback",
        "llm_qwen3_4b": "Qwen3-4B", "llm_phi4_mini": "Phi-4-mini",
        "llm_mistral7b_v03": "Mistral-7B",
    }
    ordered = [
        "cgba", "llm_mistral7b_v03", "llm_phi4_mini", "llm_qwen3_4b",
        "pairwise_contract", "no_repair", "whole_chain_rollback",
    ]
    dev_rows = []
    for arm in ordered:
        row = development["all_development_arms"][arm]
        dev_rows.append([
            arm_labels[arm], pct(row["causal_native_success"]),
            pct(row["causal_constrained_success"]), pct(row["control_native_success"]),
        ])
    write_table(
        "table_development.tex",
        ["Arm", "Native (\%)", "Constrained (\%)", "Control (\%)"], dev_rows,
        "Exposed development results. The strongest eligible local comparator is frozen before confirmation.",
    )
    write_table(
        "table_development_zh.tex",
        ["方法", "原生 (\%)", "约束 (\%)", "健康对照 (\%)"], dev_rows,
        "公开开发结果。独立确认前按预声明规则冻结最强合格局部对照。",
    )
    main_rows = []
    for arm in ordered:
        value = confirmation["arms"][arm]
        main_rows.append([
            arm_labels[arm], str(value["causal_conflicts"]["n"]),
            pct(value["causal_conflicts"]["native_success_rate"]),
            pct(value["causal_conflicts"]["constrained_success_rate"]),
            pct(value["healthy_controls"]["native_success_rate"]),
        ])
    write_table(
        "table_main.tex",
        ["Arm", "$n$", "Native (\%)", "Constrained (\%)", "Control (\%)"], main_rows,
        "Independent confirmation. Invalid mutations are excluded through one common state-matched label filter.",
    )
    write_table(
        "table_main_zh.tex",
        ["方法", "$n$", "原生 (\%)", "约束 (\%)", "健康对照 (\%)"], main_rows,
        "独立确认结果。无效变异通过各方法共用的状态匹配标签规则排除。",
    )
    class_rows = []
    class_zh = {
        "rely_gap": "依赖缺口", "role_mismatch": "角色错配",
        "clobber": "状态破坏", "stale_validation": "陈旧验证",
    }
    for conflict in ("rely_gap", "role_mismatch", "clobber", "stale_validation"):
        class_rows.append([
            conflict.replace("_", " "),
            str(method["by_class"][conflict]["n"]),
            pct(method["by_class"][conflict]["constrained_success_rate"]),
            pct(comparator["by_class"][conflict]["constrained_success_rate"]),
            pct(confirmation["arms"]["no_repair"]["by_class"][conflict]["constrained_success_rate"]),
        ])
    write_table(
        "table_classes.tex",
        ["Conflict", "$n$", "CGBAS (\%)", "Frozen comparator (\%)", "No repair (\%)"],
        class_rows, "Constrained native success by conflict class.",
    )
    class_rows_zh = [[class_zh[key], *row[1:]] for key, row in zip(
        ("rely_gap", "role_mismatch", "clobber", "stale_validation"), class_rows
    )]
    write_table(
        "table_classes_zh.tex",
        ["冲突类别", "$n$", "CGBAS (\%)", "冻结对照 (\%)", "无修复 (\%)"],
        class_rows_zh, "各冲突类别的约束原生成功率。",
    )
    environment_rows = []
    environment_rows_zh = []
    for environment, values in sorted(by_environment.items()):
        ids = {row["composition_id"] for row in values}
        comparator_values = [
            row for row in evaluated
            if row["arm"] == comparator_name and row["composition_id"] in ids
        ]
        no_values = [
            row for row in evaluated
            if row["arm"] == "no_repair" and row["composition_id"] in ids
        ]
        row = [
            environment, str(len(values)), pct(mean([v["constrained_success"] for v in values])),
            pct(mean([v["constrained_success"] for v in comparator_values])),
            pct(mean([v["constrained_success"] for v in no_values])),
        ]
        environment_rows.append(row)
        environment_rows_zh.append([
            "ALFWorld" if environment == "alfworld" else "ScienceWorld", *row[1:]
        ])
    headers = ["Environment", "$n$", "CGBAS (\%)", "Frozen comparator (\%)", "No repair (\%)"]
    write_table("table_environments.tex", headers, environment_rows, "Causal constrained success by native environment.")
    write_table(
        "table_environments_zh.tex",
        ["环境", "$n$", "CGBAS (\%)", "冻结对照 (\%)", "无修复 (\%)"],
        environment_rows_zh, "按原生环境划分的因果约束成功率。",
    )
    checks = confirmation["checks"]
    audit_rows = [[esc(key.replace("_", " ")), "Pass" if value else "Fail"] for key, value in checks.items()]
    audit_rows_zh = [[row[0], "通过" if checks[key] else "未通过"] for key, row in zip(checks, audit_rows)]
    write_table("table_audits.tex", ["Frozen check", "Result"], audit_rows, "Predeclared confirmation gates and integrity checks.")
    write_table("table_audits_zh.tex", ["冻结检查项", "结果"], audit_rows_zh, "预声明确认门槛与完整性检查。")


if __name__ == "__main__":
    main()
