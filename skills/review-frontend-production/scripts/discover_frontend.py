#!/usr/bin/env python3
"""Read-only frontend discovery hints. Candidate output is NOT an audit inventory.

Use route source, runtime navigation, feature configuration and product documents
to reconcile every candidate. No project code, package script or network is run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", ".next", ".nuxt", ".svelte-kit", ".turbo", ".cache",
    "dist", "build", "coverage", "vendor", "__pycache__", "frontend-review",
}
SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".html", ".astro"}
FRAMEWORKS = {
    "react", "react-dom", "next", "vue", "vue-router", "nuxt", "svelte",
    "@sveltejs/kit", "astro", "@angular/core", "@angular/router",
    "react-router", "react-router-dom", "@tanstack/react-router",
    "@remix-run/react", "@tanstack/react-query", "@radix-ui/react-dialog",
    "@playwright/test", "playwright", "vitest", "jest", "cypress",
    "axe-core", "@axe-core/playwright", "typescript", "vite",
}
ROUTE_PATTERN = re.compile(r"""(?:\bpath\s*[:=]|\b(?:href|to)\s*=)\s*["'](/[^"'\s]*)["']""")
COMPONENT_PATTERN = re.compile(
    r"\b(?:export\s+(?:default\s+)?)?(?:function|class|const|let)\s+([A-Z][A-Za-z0-9_]*)\b"
)


def candidate_files(root, limit):
    warnings = []
    if shutil.which("rg"):
        command = ["rg", "--files", "--hidden"]
        for folder in sorted(SKIP_DIRS):
            command.extend(["-g", f"!**/{folder}/**"])
        command.extend(["-g", "!**/.env*", "-g", "!**/*.pem", "-g", "!**/*.key"])
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        if result.returncode in (0, 1):
            paths = result.stdout.splitlines()
            if len(paths) > limit:
                warnings.append(f"File limit {limit} reached; discovery is incomplete.")
            return paths[:limit], warnings
        warnings.append("rg file listing failed; used a bounded filesystem walk.")
    paths = []
    for directory, children, files in os.walk(root, followlinks=False):
        children[:] = sorted(d for d in children if d not in SKIP_DIRS)
        for name in sorted(files):
            if name.startswith(".env") or name.endswith((".pem", ".key")):
                continue
            paths.append(str((Path(directory) / name).relative_to(root)))
            if len(paths) >= limit:
                warnings.append(f"File limit {limit} reached; discovery is incomplete.")
                return paths, warnings
    return paths, warnings


def discover(root, max_files=20000, max_bytes=262144):
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Project root must be an existing directory.")
    files, warnings = candidate_files(root, max_files)
    packages, route_files, literals, components, configurations, skipped = [], [], [], [], [], []
    for relative in files:
        path = root / relative
        if path.name.startswith(".env") or path.suffix in {".pem", ".key"}:
            continue
        if path.name != "package.json" and path.suffix not in SOURCE_SUFFIXES and not (
            path.name.startswith(("vite.config.", "next.config.", "nuxt.config.", "astro.config.",
                                  "svelte.config.", "playwright.config.", "vitest.config.", "tsconfig"))
            or path.name in {"pnpm-workspace.yaml", "angular.json"}
        ):
            continue
        try:
            path.resolve().relative_to(root)
            if not path.is_file() or path.stat().st_size > max_bytes:
                skipped.append({"path": relative, "reason": "not a regular file or exceeds size bound"})
                continue
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError):
            skipped.append({"path": relative, "reason": "unreadable, non-UTF-8 or outside project"})
            continue
        if path.name == "package.json":
            try:
                package = json.loads(source)
                dependencies = {}
                for key in ("dependencies", "devDependencies", "peerDependencies"):
                    values = package.get(key, {})
                    if isinstance(values, dict):
                        dependencies.update(values)
                scripts = package.get("scripts", {})
                packages.append({
                    "path": relative, "name": package.get("name", "unnamed"),
                    "framework_versions": {key: dependencies[key] for key in sorted(FRAMEWORKS & dependencies.keys())},
                    "script_names": sorted(scripts) if isinstance(scripts, dict) else [],
                    "package_manager": package.get("packageManager", "not declared"),
                })
            except (ValueError, AttributeError, TypeError):
                skipped.append({"path": relative, "reason": "invalid package manifest"})
            continue
        parts = Path(relative).parts
        file_stem = path.stem
        if (file_stem in {"page", "+page", "layout", "+layout", "error", "not-found", "loading"}
            or any(part in {"pages", "routes"} for part in parts)
            or file_stem.lower() in {"router", "routes", "app-routing.module"}):
            route_files.append({
                "path": relative,
                "kind": "candidate route, layout or route-state source; inspect actual framework semantics",
            })
        if ".config." in path.name or path.name.startswith("tsconfig") or path.name == "angular.json":
            configurations.append(relative)
        if path.suffix not in SOURCE_SUFFIXES:
            continue
        for match in ROUTE_PATTERN.finditer(source):
            literals.append({
                "value": match.group(1), "path": relative,
                "line": source.count("\n", 0, match.start()) + 1,
                "kind": "literal path/navigation candidate, may be a link rather than route declaration",
            })
        for match in COMPONENT_PATTERN.finditer(source):
            components.append({
                "name": match.group(1), "path": relative,
                "line": source.count("\n", 0, match.start()) + 1,
                "kind": "capitalized declaration candidate, may not be a rendered component",
            })
    return {
        "project_root": str(root),
        "discovery_level": "heuristic_candidates_only",
        "files_listed": len(files), "packages": packages,
        "route_source_candidates": route_files, "path_literal_candidates": literals,
        "component_declaration_candidates": components, "configuration_candidates": configurations,
        "skipped": skipped, "warnings": warnings,
        "must_reconcile": [
            "Resolve framework routes, dynamic parameters, aliases, guards, redirects, flags, nested and parallel routes.",
            "Inspect runtime navigation and pages reachable only through dialogs, roles, tenant settings or deep links.",
            "Map rendered UI instances, including conditionally rendered and inline components.",
            "Do not use this file as proof that all routes or components have been discovered or reviewed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--out")
    parser.add_argument("--max-files", type=int, default=20000)
    parser.add_argument("--max-bytes", type=int, default=262144)
    args = parser.parse_args()
    if args.max_files < 1 or args.max_bytes < 1:
        parser.error("Bounds must be positive.")
    try:
        result = discover(Path(args.root), args.max_files, args.max_bytes)
        content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            path = Path(args.out)
            if path.exists():
                raise ValueError("Refusing to overwrite existing discovery output; choose a new run file.")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(json.dumps({
                "output": str(path), "packages": len(result["packages"]),
                "route_source_candidates": len(result["route_source_candidates"]),
                "component_candidates": len(result["component_declaration_candidates"]),
                "warnings": result["warnings"],
            }, ensure_ascii=False))
        else:
            print(content, end="")
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
