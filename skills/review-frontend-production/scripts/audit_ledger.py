#!/usr/bin/env python3
"""Create, reconcile, validate and summarize a frontend audit ledger.

Standard library only. This validates declared records, never the application or
truthfulness of evidence. It does not discover routes, run browsers, or mark passes.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"
DIMENSIONS = {
    "project": (
        "reproducibility", "architecture", "security_boundaries",
        "delivery_observability",
    ),
    "page": (
        "routing_history", "state_coverage", "responsive_content",
        "journey_integration",
    ),
    "component": (
        "behavior", "states", "semantics_accessibility", "layout_content",
        "data_effects", "security_privacy", "performance_lifecycle",
        "maintainability_integration",
    ),
}
CONTRACT_FIELDS = (
    "responsibility", "interface", "states", "data_effects",
    "semantics_accessibility", "styling_layout", "performance_lifecycle",
    "security_privacy", "observability", "integration",
)
CONTEXT_FIELDS = ("role", "data", "network", "viewport", "input", "lifecycle")
COLLECTIONS = (
    "pages", "definitions", "instances", "scenarios", "evidence", "checks",
    "findings", "component_blueprints", "component_plans", "tasks", "release_gates",
)
CHECK_STATES = {"not_checked", "passed", "failed", "blocked", "not_applicable"}
SCENARIO_STATES = {"planned", "passed", "failed", "blocked", "not_applicable"}
FINDING_STATES = {
    "open", "in_progress", "fixed_unverified", "resolved", "accepted_risk", "dismissed",
}
TASK_STATES = {"planned", "in_progress", "implemented", "verified", "blocked", "deferred"}
EVIDENCE_KINDS = {"source", "runtime", "test", "measurement", "artifact", "specification"}
DISPOSITIONS = {"retain", "configure", "refactor", "replace", "remove", "investigate"}
FINDING_CONFIDENCE = {"confirmed", "probable", "needs_validation"}
REQUIRED_GATES = (
    ("GATE-001", "核心旅程、异常恢复及关键可访问性已验证"),
    ("GATE-002", "身份、对象、租户与字段权限在受信任边界执行"),
    ("GATE-003", "写操作的一致性、重试、取消与结果未知语义已验证"),
    ("GATE-004", "生产构建、配置与依赖安装可复现"),
    ("GATE-005", "目标环境下的性能、布局与长时间使用符合约定"),
    ("GATE-006", "错误可诊断，监控与日志数据满足隐私约定"),
    ("GATE-007", "发布、新旧版本兼容与恢复路径已验证"),
    ("GATE-008", "审查范围、基线一致性及尚存风险已明确"),
)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def text_present(value):
    return isinstance(value, str) and bool(value.strip())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("The top-level JSON value must be an object.")
    return value


def skeleton(name):
    result = {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "id": "PRJ-001", "name": name, "target": "unknown",
            "mode": "audit_plan", "review_depth": "full", "access_mode": "source_only",
            "baseline": {"source_ref": "unknown", "runtime_ref": "unknown", "observed_at": now()},
            "inventory_status": "discovering", "inventory_sources": [],
            "scope": "待根据用户请求与实际项目明确", "out_of_scope": [],
            "production_profile": {}, "assumptions": [],
        },
        **{key: [] for key in COLLECTIONS},
        "progress": {
            "current_page": None, "completed_batches": [], "next_actions": ["发现并核对全部页面与组件"],
            "unresolved_access": [], "last_updated": now(),
        },
    }
    result["release_gates"] = [
        {"id": ident, "name": title, "required": True, "status": "not_checked",
         "evidence_ids": [], "reason": ""}
        for ident, title in REQUIRED_GATES
    ]
    return result


def sync_checks(data):
    """Add missing minimum dimensions; do not modify any existing decision."""
    for key in COLLECTIONS:
        if key not in data:
            data[key] = []
        if not isinstance(data[key], list):
            raise ValueError(f"{key} must be a list before sync.")
    project = data.get("project")
    if not isinstance(project, dict) or not text_present(project.get("id")):
        raise ValueError("project.id is required before sync.")
    for key in ("pages", "instances", "checks"):
        if any(not isinstance(row, dict) for row in data[key]):
            raise ValueError(f"{key} must contain objects before sync.")
    active_pages = {
        p["id"] for p in data["pages"]
        if text_present(p.get("id")) and p.get("scope_status", "in_scope") == "in_scope"
    }
    targets = [("project", project["id"])]
    targets.extend(("page", ident) for ident in sorted(active_pages))
    targets.extend(
        ("component", row["id"]) for row in data["instances"]
        if text_present(row.get("id")) and row.get("page_id") in active_pages
    )
    existing = {
        (row.get("scope"), row.get("target_id"), row.get("dimension"))
        for row in data["checks"]
    }
    used = {
        row.get("id") for key in COLLECTIONS for row in data[key]
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    number = 1
    added = 0
    for scope, target in targets:
        for dimension in DIMENSIONS[scope]:
            if (scope, target, dimension) in existing:
                continue
            while f"CHK-{number:04d}" in used:
                number += 1
            ident = f"CHK-{number:04d}"
            used.add(ident)
            data["checks"].append({
                "id": ident, "scope": scope, "target_id": target, "dimension": dimension,
                "question": f"待细化：{target} 的 {dimension} 在哪些条件下满足哪些具体预期？",
                "status": "not_checked", "evidence_ids": [], "scenario_ids": [],
                "finding_ids": [], "reason": "",
            })
            number += 1
            added += 1
    progress = data.setdefault("progress", {})
    if isinstance(progress, dict):
        progress["last_updated"] = now()
    return added


def validate(data):
    errors, warnings = [], []
    tables = {}
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}.")
    project = data.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object.")
        project = {}
    for key in ("id", "name", "target", "scope"):
        if not text_present(project.get(key)):
            errors.append(f"project.{key} must be a non-empty string.")
    if project.get("review_depth", "full") not in {"quick", "full"}:
        errors.append("project.review_depth is invalid.")
    if project.get("mode") not in {"audit_plan", "implement"}:
        errors.append("project.mode is invalid.")
    if project.get("access_mode") not in {"source_runtime", "source_only", "runtime_only", "screenshots_only"}:
        errors.append("project.access_mode is invalid.")
    if project.get("inventory_status") not in {"discovering", "reconciled", "limited"}:
        errors.append("project.inventory_status is invalid.")
    if not isinstance(project.get("baseline"), dict):
        errors.append("project.baseline must be an object.")
    else:
        for key in ("source_ref", "runtime_ref", "observed_at"):
            if not text_present(project["baseline"].get(key)):
                errors.append(f"project.baseline.{key} must be a non-empty string.")
    if not isinstance(project.get("production_profile"), dict):
        errors.append("project.production_profile must be an object.")

    seen_global = {project.get("id")} if text_present(project.get("id")) else set()
    for key in COLLECTIONS:
        rows = data.get(key)
        if not isinstance(rows, list):
            errors.append(f"{key} must be a list.")
            rows = []
        valid_rows = []
        index = {}
        for number, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"{key}[{number}] must be an object.")
                continue
            valid_rows.append(row)
            if key == "component_plans":
                ident = row.get("instance_id")
                if not text_present(ident):
                    errors.append(f"{key}[{number}].instance_id is required.")
                    continue
                if ident in index:
                    errors.append(f"Duplicate component plan for {ident}.")
            else:
                ident = row.get("id")
                if not text_present(ident):
                    errors.append(f"{key}[{number}].id is required.")
                    continue
                if ident in seen_global:
                    errors.append(f"Duplicate entity id {ident}.")
                seen_global.add(ident)
            index[ident] = row
        tables[key] = (valid_rows, index)

    def rows(key):
        return tables[key][0]

    def index(key):
        return tables[key][1]

    def required(row, fields, label):
        for field in fields:
            if not text_present(row.get(field)):
                errors.append(f"{label}.{field} must be a non-empty string.")

    def strings(row, field, label, nonempty=False):
        value = row.get(field)
        if not isinstance(value, list):
            errors.append(f"{label}.{field} must be a list.")
            return []
        if nonempty and not value:
            errors.append(f"{label}.{field} must not be empty.")
        if any(not text_present(x) for x in value):
            errors.append(f"{label}.{field} must contain non-empty strings.")
        return [x for x in value if text_present(x)]

    def refs(row, field, target, label, nonempty=False):
        value = strings(row, field, label, nonempty)
        available = index(target) if isinstance(target, str) else target
        for ident in value:
            if ident not in available:
                errors.append(f"{label}.{field} refers to unknown {ident}.")
        return value

    strings(project, "assumptions", "project")
    for key, fields in (
        ("inventory_sources", ("kind", "locator")),
        ("out_of_scope", ("surface", "reason", "authority")),
    ):
        values = project.get(key)
        if not isinstance(values, list):
            errors.append(f"project.{key} must be a list.")
            continue
        for number, row in enumerate(values):
            label = f"project.{key}[{number}]"
            if not isinstance(row, dict):
                errors.append(f"{label} must be an object.")
                continue
            required(row, fields, label)
            if key == "inventory_sources":
                refs(row, "evidence_ids", "evidence", label,
                     project.get("inventory_status") == "reconciled")

    progress = data.get("progress")
    if not isinstance(progress, dict):
        errors.append("progress must be an object.")
    else:
        for key in ("completed_batches", "next_actions", "unresolved_access"):
            strings(progress, key, "progress")
        required(progress, ("last_updated",), "progress")
        current_page = progress.get("current_page")
        if "current_page" not in progress or current_page is not None and (
            not text_present(current_page) or current_page not in index("pages")
        ):
            errors.append("progress.current_page must be null or a known page id.")

    for row in rows("evidence"):
        label = row.get("id", "evidence")
        required(row, ("locator", "observed_at", "baseline_ref", "summary"), label)
        if row.get("kind") not in EVIDENCE_KINDS:
            errors.append(f"{label}.kind is invalid.")

    page_map, instance_map, scenario_map = index("pages"), index("instances"), index("scenarios")
    for row in rows("pages"):
        label = row.get("id", "page")
        required(row, ("route", "title", "source_locator"), label)
        strings(row, "entry_conditions", label)
        strings(row, "variants", label)
        refs(row, "evidence_ids", "evidence", label)
        if row.get("scope_status") not in {"in_scope", "excluded"}:
            errors.append(f"{label}.scope_status is invalid.")
        if row.get("scope_status") == "excluded":
            required(row, ("exclusion_reason", "exclusion_authority"), label)

    for row in rows("definitions"):
        label = row.get("id", "definition")
        required(row, ("name", "kind", "source_locator"), label)
        if row.get("source_status") not in {"located", "unavailable", "inferred"}:
            errors.append(f"{label}.source_status is invalid.")

    for row in rows("instances"):
        label = row.get("id", "instance")
        required(row, ("label", "locator", "variant"), label)
        if row.get("page_id") not in page_map:
            errors.append(f"{label}.page_id is unknown.")
        if row.get("definition_id") not in index("definitions"):
            errors.append(f"{label}.definition_id is unknown.")
        if row.get("criticality") not in {"high", "normal"}:
            errors.append(f"{label}.criticality is invalid.")
        parent = row.get("parent_instance_id")
        if parent is not None:
            if parent not in instance_map:
                errors.append(f"{label}.parent_instance_id is unknown.")
            elif instance_map[parent].get("page_id") != row.get("page_id"):
                errors.append(f"{label} and its parent must belong to the same page.")
            if parent == row.get("id"):
                errors.append(f"{label} cannot parent itself.")

    parent_paths_checked = set()
    for ident in instance_map:
        path, positions, current = [], {}, ident
        while current in instance_map and current not in parent_paths_checked:
            if current in positions:
                cycle = path[positions[current]:] + [current]
                if len(cycle) > 2:  # Direct self-parenting is reported above.
                    errors.append("Component parent cycle: " + " -> ".join(cycle))
                break
            positions[current] = len(path)
            path.append(current)
            parent = instance_map[current].get("parent_instance_id")
            if not isinstance(parent, str):
                break
            current = parent
        parent_paths_checked.update(path)

    def evidence_kinds(row, field="evidence_ids"):
        return {
            index("evidence")[ident].get("kind")
            for ident in row.get(field, []) if isinstance(ident, str) and ident in index("evidence")
        } if isinstance(row.get(field), list) else set()

    def result_fields(row, label, states):
        status = row.get("status")
        if status not in states:
            errors.append(f"{label}.status is invalid.")
        if not isinstance(row.get("reason"), str):
            errors.append(f"{label}.reason must be a string (empty is allowed unless a reason is required).")
        refs(row, "evidence_ids", "evidence", label, status in {"passed", "failed"})
        if status in {"blocked", "not_applicable"}:
            required(row, ("reason",), label)

    for row in rows("scenarios"):
        label = row.get("id", "scenario")
        required(row, ("title",), label)
        page_ids = refs(row, "page_ids", "pages", label, True)
        instance_ids = refs(row, "instance_ids", "instances", label)
        strings(row, "preconditions", label)
        strings(row, "steps", label, True)
        strings(row, "expected", label, True)
        context = row.get("context")
        if not isinstance(context, dict):
            errors.append(f"{label}.context must be an object.")
        else:
            for key in CONTEXT_FIELDS:
                value = context.get(key)
                if isinstance(value, list):
                    descriptions = strings(context, key, label + ".context", True)
                elif text_present(value):
                    descriptions = [value]
                else:
                    errors.append(f"{label}.context.{key} must be a non-empty string or string list.")
                    descriptions = []
                if descriptions and all(
                    value.strip().lower().rstrip(":：").strip()
                    in {"n/a", "na", "not_applicable", "not applicable", "不适用"}
                    for value in descriptions
                ):
                    errors.append(f"{label}.context.{key} must explain why it is not applicable.")
        if row.get("risk") not in {"high", "normal"}:
            errors.append(f"{label}.risk is invalid.")
        result_fields(row, label, SCENARIO_STATES)
        refs(row, "finding_ids", "findings", label, row.get("status") == "failed")
        for ident in instance_ids:
            if ident in instance_map and instance_map[ident].get("page_id") not in page_ids:
                errors.append(f"{label} omits the page of {ident}.")
        if row.get("status") in {"passed", "failed"} and not (evidence_kinds(row) & {"runtime", "test"}):
            errors.append(f"{label} {row.get('status')} requires actual runtime or test evidence.")

    scope_indexes = {"project": {project.get("id"): project}, "page": page_map, "component": instance_map}
    for row in rows("checks"):
        label = row.get("id", "check")
        required(row, ("question",), label)
        scope = row.get("scope")
        if scope not in DIMENSIONS:
            errors.append(f"{label}.scope is invalid.")
        elif row.get("target_id") not in scope_indexes[scope]:
            errors.append(f"{label}.target_id is unknown for {scope}.")
        if scope in DIMENSIONS and row.get("dimension") not in DIMENSIONS[scope]:
            errors.append(f"{label}.dimension is invalid for {scope}.")
        result_fields(row, label, CHECK_STATES)
        refs(row, "finding_ids", "findings", label, row.get("status") == "failed")
        scenario_ids = refs(row, "scenario_ids", "scenarios", label)
        for ident in scenario_ids:
            if ident not in scenario_map:
                continue
            scenario = scenario_map[ident]
            if scope == "page" and row.get("target_id") not in scenario.get("page_ids", []):
                errors.append(f"{label} references {ident} outside its page scope.")
            if scope == "component" and row.get("target_id") not in scenario.get("instance_ids", []):
                errors.append(f"{label} references {ident} outside its component scope.")
            if row.get("status") == "passed" and scenario.get("status") != "passed":
                errors.append(f"{label} cannot pass with unpassed scenario {ident}.")
        if row.get("status") == "passed":
            kinds = evidence_kinds(row)
            if row.get("dimension") in {
                "behavior", "states", "routing_history", "state_coverage", "journey_integration",
            }:
                if not (kinds & {"runtime", "test"}) or not scenario_ids:
                    errors.append(f"{label} needs runtime/test evidence and linked scenarios.")
            if row.get("dimension") in {"architecture", "maintainability_integration"} and "source" not in kinds:
                errors.append(f"{label} needs source evidence.")
            if row.get("dimension") == "performance_lifecycle" and not (
                kinds & {"runtime", "test", "measurement"}
            ):
                errors.append(f"{label} needs runtime/test/measurement evidence.")

    for row in rows("findings"):
        label = row.get("id", "finding")
        required(row, (
            "title", "category", "owner", "actual", "expected", "impact",
            "root_cause", "root_cause_confidence", "remediation", "regression_test",
        ), label)
        if row.get("severity") not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"{label}.severity is invalid.")
        if row.get("confidence") not in FINDING_CONFIDENCE:
            errors.append(f"{label}.confidence is invalid.")
        if row.get("status") not in FINDING_STATES:
            errors.append(f"{label}.status is invalid.")
        for field, target in (
            ("page_ids", "pages"), ("instance_ids", "instances"),
            ("definition_ids", "definitions"), ("check_ids", "checks"), ("scenario_ids", "scenarios"),
        ):
            linked_ids = refs(row, field, target, label)
            if row.get("status") == "resolved" and target in {"checks", "scenarios"}:
                for ident in linked_ids:
                    if ident in index(target) and index(target)[ident].get("status") not in {"passed", "not_applicable"}:
                        errors.append(f"{label} resolved contradicts the current status of {ident}.")
        refs(row, "evidence_ids", "evidence", label, row.get("confidence") == "confirmed")
        refs(row, "resolution_evidence_ids", "evidence", label, row.get("status") == "resolved")
        if row.get("status") == "resolved" and not (
            evidence_kinds(row, "resolution_evidence_ids") & {"source", "runtime", "test", "measurement"}
        ):
            errors.append(f"{label} resolved needs source/runtime/test/measurement resolution evidence.")
        reproduction = row.get("reproduction")
        if not isinstance(reproduction, dict):
            errors.append(f"{label}.reproduction must be an object.")
        else:
            strings(reproduction, "preconditions", label + ".reproduction")
            strings(reproduction, "steps", label + ".reproduction", True)
        if row.get("status") in {"accepted_risk", "dismissed"}:
            decision = row.get("decision")
            if not isinstance(decision, dict):
                errors.append(f"{label} needs an explicit decision.")
            else:
                required(decision, ("reason", "authority"), label + ".decision")
        for ident in row.get("instance_ids", []) if isinstance(row.get("instance_ids"), list) else []:
            if isinstance(ident, str) and ident in instance_map:
                page_ids = row.get("page_ids")
                if not isinstance(page_ids, list) or instance_map[ident].get("page_id") not in page_ids:
                    errors.append(f"{label} omits the affected page of {ident}.")

    for collection in ("checks", "scenarios"):
        for row in rows(collection):
            for ident in row.get("finding_ids", []) if isinstance(row.get("finding_ids"), list) else []:
                if not isinstance(ident, str) or ident not in index("findings"):
                    continue
                finding = index("findings")[ident]
                if row.get("status") == "failed" and finding.get("confidence") != "confirmed":
                    errors.append(f"{row.get('id')} failed references unconfirmed finding {ident}.")
                forward_ids = finding.get("check_ids" if collection == "checks" else "scenario_ids", [])
                if (finding.get("status") == "resolved" and row.get("status") not in {"passed", "not_applicable"}
                    and (not isinstance(forward_ids, list) or row.get("id") not in forward_ids)):
                    errors.append(f"{row.get('id')} cannot remain {row.get('status')} for resolved finding {ident}.")

    for row in rows("component_blueprints"):
        label = row.get("id", "blueprint")
        required(row, ("current_contract",), label)
        if row.get("definition_id") not in index("definitions"):
            errors.append(f"{label}.definition_id is unknown.")
        strings(row, "change_locations", label, True)
        contract = row.get("target_contract")
        if not isinstance(contract, dict):
            errors.append(f"{label}.target_contract must be an object.")
        else:
            required(contract, CONTRACT_FIELDS, label + ".target_contract")

    for row in rows("component_plans"):
        label = "plan:" + str(row.get("instance_id", "unknown"))
        instance_id = row.get("instance_id")
        if instance_id not in instance_map:
            errors.append(f"{label} refers to an unknown instance.")
        if row.get("blueprint_id") not in index("component_blueprints"):
            errors.append(f"{label}.blueprint_id is unknown.")
        elif instance_id in instance_map:
            blueprint = index("component_blueprints")[row["blueprint_id"]]
            if blueprint.get("definition_id") != instance_map[instance_id].get("definition_id"):
                errors.append(f"{label} uses a blueprint for a different current definition.")
        if row.get("disposition") not in DISPOSITIONS:
            errors.append(f"{label}.disposition is invalid.")
        required(row, ("rationale",), label)
        strings(row, "instance_changes", label)
        strings(row, "acceptance_criteria", label, True)
        refs(row, "finding_ids", "findings", label)
        refs(row, "task_ids", "tasks", label, row.get("disposition") != "retain")
        scenario_ids = refs(row, "regression_scenario_ids", "scenarios", label, True)
        for ident in scenario_ids:
            if ident in scenario_map and instance_id not in scenario_map[ident].get("instance_ids", []):
                errors.append(f"{label} regression {ident} does not cover this instance.")

    scope_ids = set(scope_indexes["project"]) | set(page_map) | set(instance_map) | set(index("definitions"))
    for row in rows("tasks"):
        label = row.get("id", "task")
        required(row, ("title", "owner", "rollback", "risk"), label)
        if row.get("status") not in TASK_STATES:
            errors.append(f"{label}.status is invalid.")
        if not isinstance(row.get("phase"), int) or isinstance(row.get("phase"), bool) or row.get("phase", -1) < 0:
            errors.append(f"{label}.phase must be a non-negative integer.")
        for field in ("change_locations", "implementation_steps", "acceptance_criteria"):
            strings(row, field, label, True)
        refs(row, "scope_ids", scope_ids, label, True)
        refs(row, "finding_ids", "findings", label)
        dependencies = refs(row, "depends_on", "tasks", label)
        scenario_ids = refs(row, "verification_scenario_ids", "scenarios", label, True)
        refs(row, "evidence_ids", "evidence", label, row.get("status") == "verified")
        if row.get("status") == "verified":
            if not (evidence_kinds(row) & {"runtime", "test", "measurement"}):
                errors.append(f"{label} verified needs actual runtime/test/measurement evidence.")
            passed_scenarios = 0
            for ident in scenario_ids:
                scenario = scenario_map.get(ident)
                if scenario is None:
                    continue
                if scenario.get("status") == "passed":
                    passed_scenarios += 1
                elif scenario.get("status") != "not_applicable" or not text_present(scenario.get("reason")):
                    errors.append(f"{label} verified requires passed or justified not_applicable scenario {ident}.")
            if not passed_scenarios:
                errors.append(f"{label} verified needs at least one passed verification scenario.")
            for ident in dependencies:
                if ident in index("tasks") and index("tasks")[ident].get("status") != "verified":
                    errors.append(f"{label} verified requires verified dependency {ident}.")

    task_map = index("tasks")
    marks = {}

    def visit(ident, path):
        if marks.get(ident) == 1:
            errors.append("Task dependency cycle: " + " -> ".join(path + [ident]))
            return
        if marks.get(ident) == 2:
            return
        marks[ident] = 1
        row = task_map[ident]
        dependencies = row.get("depends_on", [])
        if not isinstance(dependencies, list):
            dependencies = []
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in task_map:
                continue
            phase, previous = row.get("phase"), task_map[dependency].get("phase")
            if isinstance(phase, int) and isinstance(previous, int) and previous > phase:
                errors.append(f"{ident} is scheduled before dependency {dependency}.")
            visit(dependency, path + [ident])
        marks[ident] = 2

    for ident in task_map:
        visit(ident, [])

    for row in rows("release_gates"):
        label = row.get("id", "gate")
        required(row, ("name",), label)
        if not isinstance(row.get("required"), bool):
            errors.append(f"{label}.required must be boolean.")
        result_fields(row, label, CHECK_STATES)
        if row.get("required") is False:
            required(row, ("reason",), label)
        if row.get("required") and row.get("status") == "not_applicable":
            errors.append(f"{label} cannot be required and not_applicable; justify scope explicitly.")

    active_pages = {ident for ident, row in page_map.items() if row.get("scope_status") == "in_scope"}
    active_instances = {
        ident for ident, row in instance_map.items() if row.get("page_id") in active_pages
    }
    applicable_checks = [
        row for row in rows("checks")
        if row.get("scope") == "project"
        or row.get("scope") == "page" and row.get("target_id") in active_pages
        or row.get("scope") == "component" and row.get("target_id") in active_instances
    ]
    represented = {
        (row.get("scope"), row.get("target_id"), row.get("dimension"))
        for row in applicable_checks
    }
    expected = {
        (scope, ident, dimension)
        for scope, identifiers in (
            ("project", [project.get("id")]), ("page", active_pages), ("component", active_instances)
        )
        for ident in identifiers for dimension in DIMENSIONS[scope]
    }
    missing_dimensions = sorted(expected - represented, key=str)
    pages_without_instances = sorted(
        ident for ident in active_pages
        if not any(row.get("page_id") == ident for row in rows("instances"))
    )
    page_scenarios, instance_scenarios = set(), set()
    high_risk_instances_covered = set()
    for row in rows("scenarios"):
        if row.get("status") == "not_applicable":
            continue
        page_scenarios.update(x for x in row.get("page_ids", []) if isinstance(x, str)) if isinstance(row.get("page_ids"), list) else None
        instance_scenarios.update(x for x in row.get("instance_ids", []) if isinstance(x, str)) if isinstance(row.get("instance_ids"), list) else None
        if row.get("risk") == "high" and isinstance(row.get("instance_ids"), list):
            high_risk_instances_covered.update(x for x in row["instance_ids"] if isinstance(x, str))
    missing_page_scenarios = sorted(active_pages - page_scenarios)
    missing_instance_scenarios = sorted(active_instances - instance_scenarios)
    missing_high_risk = sorted(
        ident for ident in active_instances
        if instance_map[ident].get("criticality") == "high" and ident not in high_risk_instances_covered
    )
    missing_plans = sorted(active_instances - set(index("component_plans")))
    planned_definitions = {
        row.get("definition_id") for row in rows("component_blueprints")
        if text_present(row.get("definition_id"))
    }
    missing_blueprints = sorted(set(index("definitions")) - planned_definitions)
    planned_findings = {
        ident for row in rows("tasks") if isinstance(row.get("finding_ids"), list)
        for ident in row["finding_ids"] if isinstance(ident, str)
    }
    unplanned_findings = sorted(
        ident for ident, row in index("findings").items()
        if row.get("status") not in {"accepted_risk", "dismissed"} and ident not in planned_findings
    )
    critical_open = sorted(
        ident for ident, row in index("findings").items()
        if row.get("severity") in {"P0", "P1"} and row.get("status") not in {"resolved", "dismissed"}
    )
    active_scenarios = [
        row for row in rows("scenarios")
        if isinstance(row.get("page_ids"), list) and active_pages.intersection(
            ident for ident in row["page_ids"] if isinstance(ident, str)
        )
    ]
    check_counts = Counter(row.get("status", "invalid") for row in applicable_checks)
    scenario_counts = Counter(row.get("status", "invalid") for row in active_scenarios)
    inventory_sources = project.get("inventory_sources", [])
    inventory_sources = inventory_sources if isinstance(inventory_sources, list) else []
    if project.get("inventory_status") == "reconciled":
        if not inventory_sources:
            errors.append("Reconciled inventory needs source records.")
        if len({s.get("kind") for s in inventory_sources if isinstance(s, dict) and text_present(s.get("kind"))}) < 2:
            warnings.append("Only one inventory channel: justify discovery limitations; the script cannot establish completeness.")
    if not active_pages:
        warnings.append("No in-scope pages have been inventoried.")
    if not active_instances:
        warnings.append("No in-scope component instances have been inventoried.")
    if project.get("access_mode") != "source_runtime":
        warnings.append("Limited access: do not claim a full source-and-runtime production review.")
    if not project.get("production_profile"):
        warnings.append("Production profile is not defined.")
    coverage_gaps = {
        "missing_dimensions": [list(item) for item in missing_dimensions],
        "pages_without_instances": pages_without_instances,
        "pages_without_scenarios": missing_page_scenarios,
        "instances_without_scenarios": missing_instance_scenarios,
        "high_risk_instances_without_high_risk_scenarios": missing_high_risk,
        "definitions_without_blueprints": missing_blueprints,
        "instances_without_plans": missing_plans,
        "findings_without_tasks": unplanned_findings,
    }
    structural_gaps = any(value for key, value in coverage_gaps.items()
                          if key not in {"definitions_without_blueprints", "instances_without_plans", "findings_without_tasks"})
    coverage_closed = bool(
        not errors and active_pages and active_instances
        and project.get("review_depth", "full") == "full"
        and project.get("inventory_status") == "reconciled"
        and not structural_gaps
        and not check_counts["not_checked"] and not check_counts["blocked"]
        and not scenario_counts["planned"] and not scenario_counts["blocked"]
    )
    plan_complete = bool(
        not errors and active_pages and active_instances
        and project.get("review_depth", "full") == "full"
        and not missing_blueprints and not missing_plans and not unplanned_findings
    )
    required_gates = [row for row in rows("release_gates") if row.get("required")]
    source_and_execution = (
        any(row.get("kind") == "source" for row in rows("evidence"))
        and any(row.get("kind") in {"runtime", "test"} for row in rows("evidence"))
    )
    gates_satisfied = bool(
        coverage_closed and plan_complete and project.get("access_mode") == "source_runtime"
        and project.get("production_profile") and source_and_execution
        and not check_counts["failed"] and not scenario_counts["failed"] and not critical_open
        and required_gates and all(row.get("status") == "passed" for row in required_gates)
    )
    return {
        "schema_valid": not errors, "errors": errors, "warnings": warnings,
        "counts": {
            "pages_in_scope": len(active_pages), "pages_excluded": len(page_map) - len(active_pages),
            "definitions": len(index("definitions")), "instances_in_scope": len(active_instances),
            "checks": dict(sorted(check_counts.items())), "scenarios": dict(sorted(scenario_counts.items())),
            "findings": dict(sorted(Counter(row.get("severity", "invalid") for row in rows("findings")).items())),
            "component_plans": len(index("component_plans")), "tasks": len(task_map),
        },
        "gaps": coverage_gaps, "critical_unresolved": critical_open,
        "audit_coverage_closed": coverage_closed, "plan_complete": plan_complete,
        "production_gates_satisfied": gates_satisfied,
        "disclaimer": "Mechanical validation of declared scope and records only; no application execution or security certification.",
    }


def escape(value):
    return str(value if value is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace("|", r"\|").replace("\r", "").replace("\n", " / ")


def render(data, result):
    project = data.get("project", {})
    lines = [
        "# 前端审查覆盖索引", "",
        f"项目：{escape(project.get('name'))}", "",
        f"目标：{escape(project.get('target'))}", "",
        f"访问范围：{escape(project.get('access_mode'))}；发现状态：{escape(project.get('inventory_status'))}", "",
        "> 本文件由台账生成。结构校验不验证证据真实性，也不等于产品认证。", "",
        "## 覆盖结论", "",
    ]
    for key in ("schema_valid", "audit_coverage_closed", "plan_complete", "production_gates_satisfied"):
        lines.append(f"- {key}: {result[key]}")
    lines.extend(["", "## 分母与状态", "", "~~~json",
                  json.dumps(result["counts"], ensure_ascii=False, indent=2), "~~~", ""])
    lines.extend(["## 页面与组件实例", "",
                  "| 页面 | 路由 | 组件实例 | 已通过 / 失败 / 阻塞 / 未检查 / 不适用 |",
                  "|---|---|---|---|"])
    instances = [r for r in data.get("instances", []) if isinstance(r, dict)]
    checks = [r for r in data.get("checks", []) if isinstance(r, dict)]
    for page in data.get("pages", []):
        if not isinstance(page, dict):
            continue
        members = {r.get("id") for r in instances if r.get("page_id") == page.get("id")}
        counts = Counter(
            r.get("status") for r in checks
            if r.get("scope") == "page" and r.get("target_id") == page.get("id")
            or r.get("scope") == "component" and r.get("target_id") in members
        )
        values = " / ".join(str(counts[s]) for s in ("passed", "failed", "blocked", "not_checked", "not_applicable"))
        lines.append(f"| {escape(page.get('id'))} {escape(page.get('title'))} | {escape(page.get('route'))} | {len(members)} | {values} |")
    lines.extend(["", "## 组件处置", "", "| 实例 | 蓝图 | 处置 | 任务 | 理由 |", "|---|---|---|---|---|"])
    for row in data.get("component_plans", []):
        if not isinstance(row, dict):
            continue
        values = (row.get("instance_id"), row.get("blueprint_id"), row.get("disposition"),
                  ", ".join(row.get("task_ids", [])), row.get("rationale"))
        lines.append("| " + " | ".join(escape(x) for x in values) + " |")
    lines.extend(["", "## 问题索引", "", "| 问题 | 级别 | 置信度 | 状态 | 页面 / 实例 |",
                  "|---|---|---|---|---|"])
    for row in data.get("findings", []):
        if not isinstance(row, dict):
            continue
        values = (str(row.get("id", "")) + " " + str(row.get("title", "")),
                  row.get("severity"), row.get("confidence"), row.get("status"),
                  ", ".join(row.get("page_ids", []) + row.get("instance_ids", [])))
        lines.append("| " + " | ".join(escape(x) for x in values) + " |")
    lines.extend(["", "## 任务顺序", "", "| 任务 | 阶段 | 负责人 | 依赖 | 状态 |",
                  "|---|---|---|---|---|"])
    for row in sorted(data.get("tasks", []), key=lambda r: (r.get("phase", 0), r.get("id", ""))):
        values = (str(row.get("id", "")) + " " + str(row.get("title", "")),
                  row.get("phase"), row.get("owner"), ", ".join(row.get("depends_on", [])), row.get("status"))
        lines.append("| " + " | ".join(escape(x) for x in values) + " |")
    lines.extend(["", "## 发布门槛", "", "| 门槛 | 必需 | 状态 | 证据 / 理由 |", "|---|---|---|---|"])
    for row in data.get("release_gates", []):
        values = (row.get("name"), row.get("required"), row.get("status"),
                  ", ".join(row.get("evidence_ids", [])) + " " + row.get("reason", ""))
        lines.append("| " + " | ".join(escape(x) for x in values) + " |")
    lines.extend(["", "## 缺口", ""])
    for key, values in result["gaps"].items():
        if values:
            lines.append(f"- {key}: {escape(json.dumps(values, ensure_ascii=False))}")
    for group in ("errors", "warnings"):
        if result[group]:
            lines.extend(["", f"## {group}", ""])
            lines.extend("- " + escape(message) for message in result[group])
    lines.extend(["", "## 下一步", ""])
    progress = data.get("progress", {})
    if isinstance(progress, dict):
        lines.extend("- " + escape(x) for x in progress.get("next_actions", []))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("init", help="Create a new empty ledger without overwriting an existing file.")
    create.add_argument("path")
    create.add_argument("--name", required=True)
    sync = sub.add_parser("sync", help="Add missing minimum checks; never mark anything passed.")
    sync.add_argument("path")
    check = sub.add_parser("check", help="Validate structure and report coverage.")
    check.add_argument("path")
    check.add_argument("--require-plan", action="store_true")
    check.add_argument("--require-complete", action="store_true")
    check.add_argument("--require-ready", action="store_true")
    output = sub.add_parser("render", help="Generate a coverage index from a structurally valid ledger.")
    output.add_argument("path")
    output.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            if Path(args.path).exists():
                raise ValueError("Refusing to overwrite an existing ledger.")
            data = skeleton(args.name)
            sync_checks(data)
            write_json(args.path, data)
            print(json.dumps({"created": str(Path(args.path)), "checks": len(data["checks"])}, ensure_ascii=False))
            return 0
        data = load_json(args.path)
        if args.command == "sync":
            updated = copy.deepcopy(data)
            added = sync_checks(updated)
            write_json(args.path, updated)
            print(json.dumps({"added_checks": added, "total_checks": len(updated["checks"])}, ensure_ascii=False))
            return 0
        result = validate(data)
        if args.command == "render":
            if not result["schema_valid"]:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1
            if Path(args.out).resolve() == Path(args.path).resolve():
                raise ValueError("The report path must differ from the ledger path.")
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render(data, result), encoding="utf-8")
            print(json.dumps({"rendered": str(path)}, ensure_ascii=False))
            return 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["schema_valid"]:
            return 1
        unmet = (
            args.require_plan and not result["plan_complete"]
            or args.require_complete and not result["audit_coverage_closed"]
            or args.require_ready and not result["production_gates_satisfied"]
        )
        return 2 if unmet else 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
