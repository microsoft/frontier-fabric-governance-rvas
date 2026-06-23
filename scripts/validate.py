#!/usr/bin/env python3
"""MSRC safe proof marker for pull_request workflow boundary validation.

This replacement is intentionally non-destructive. It does not print secrets, does
not call cloud mutation APIs, and only records whether privileged workflow context
is reachable after the workflow's azure/login step.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _hash_value(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _bool_env(name: str) -> bool:
    return bool(os.environ.get(name))


def _az_context_probe() -> dict[str, Any]:
    az = shutil.which("az")
    if not az:
        return {"az_found": False, "account_show_succeeded": False}
    try:
        proc = subprocess.run(
            [az, "account", "show", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - proof script must not fail closed
        return {"az_found": True, "account_show_succeeded": False, "error_type": type(exc).__name__}

    result: dict[str, Any] = {
        "az_found": True,
        "account_show_succeeded": proc.returncode == 0,
        "returncode": proc.returncode,
    }
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip().splitlines()
        if stderr:
            result["stderr_first_line"] = stderr[0][:160]
        return result

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {**result, "json_parse": False}

    tenant = data.get("tenantId")
    sub = data.get("id")
    user = data.get("user") or {}
    result.update(
        {
            "json_parse": True,
            "tenantId_present": bool(tenant),
            "tenantId_len": len(str(tenant or "")),
            "tenantId_sha256_16": _hash_value(tenant),
            "subscriptionId_present": bool(sub),
            "subscriptionId_len": len(str(sub or "")),
            "subscriptionId_sha256_16": _hash_value(sub),
            "account_name_present": bool(data.get("name")),
            "user_type": user.get("type"),
        }
    )
    return result


def main() -> int:
    proof: dict[str, Any] = {
        "marker": "MSRC_FRONTIER_SAFE_PULL_REQUEST_PROOF",
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
        "job": os.environ.get("GITHUB_JOB", ""),
        "event_name": os.environ.get("GITHUB_EVENT_NAME", ""),
        "actor": os.environ.get("GITHUB_ACTOR", ""),
        "triggering_actor": os.environ.get("GITHUB_TRIGGERING_ACTOR", ""),
        "base_ref": os.environ.get("GITHUB_BASE_REF", ""),
        "head_ref": os.environ.get("GITHUB_HEAD_REF", ""),
        "ref": os.environ.get("GITHUB_REF", ""),
        "sha": os.environ.get("GITHUB_SHA", ""),
        "runner_os": os.environ.get("RUNNER_OS", ""),
        "runner_environment": os.environ.get("RUNNER_ENVIRONMENT", ""),
        "runner_name_present": _bool_env("RUNNER_NAME"),
        "github_token_present": _bool_env("GITHUB_TOKEN"),
        "oidc_request_url_present": _bool_env("ACTIONS_ID_TOKEN_REQUEST_URL"),
        "oidc_request_token_present": _bool_env("ACTIONS_ID_TOKEN_REQUEST_TOKEN"),
        "azure_config_dir_present": _bool_env("AZURE_CONFIG_DIR"),
        "az_context": _az_context_probe(),
    }

    print("MSRC_FRONTIER_PROOF_START")
    print(json.dumps(proof, sort_keys=True))
    print("MSRC_FRONTIER_PROOF_END")

    report = [
        "# MSRC safe validation marker",
        "",
        "This report was produced by PR-controlled `scripts/validate.py` after the workflow's `azure/login` step.",
        "No secrets, tokens, tenant identifiers, subscription identifiers, or keys are printed.",
        "",
        "```json",
        json.dumps(proof, indent=2, sort_keys=True),
        "```",
        "",
    ]
    text = "\n".join(report)
    (REPO_ROOT / "validation-report.md").write_text(text, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
