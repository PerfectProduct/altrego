"""Execute the reviewed upstream RBAC runner without parsing its console output.

The upstream suite is not pytest-collectable and conditionally omits dependent
checks. Keep its assertions/order intact; report omissions in a fixed denominator.
Only mounted, evaluator-owned source is imported. Never import submitted code.
"""

import importlib.util
import json
from pathlib import Path
import sys

EXPECTED = (
    "test_create_role", "test_create_multiple_roles", "test_assign_permissions_to_role",
    "test_assign_role_to_user", "test_check_user_permissions", "test_multiple_roles_permissions",
    "test_duplicate_role_error", "test_invalid_role_id", "test_user_without_roles",
)


def main():
    spec = importlib.util.spec_from_file_location("upstream_rbac", "/oracle/test_rbac_service.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tester = module.RBACServiceTester(module.BASE_URL)
    error = None
    try:
        tester.run_all_tests()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    observed = {row["test_name"]: row for row in tester.test_results}
    rows = [observed.get(name, {"test_name": name, "status": "SKIPPED",
                              "message": "Upstream runner omitted dependent test"}) for name in EXPECTED]
    passed = sum(row["status"] == "PASS" for row in rows)
    failed = sum(row["status"] == "FAIL" for row in rows)
    skipped = sum(row["status"] == "SKIPPED" for row in rows)
    result = {"tests": {"collected_in_report": len(EXPECTED), "passed": passed,
                        "failed": failed, "skipped": skipped, "errors": int(error is not None)},
              "upstream_observed": tester.test_results, "fixed_denominator": rows,
              "runner_error": error}
    Path("/results/rbac.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if passed == len(EXPECTED) and error is None else 1


if __name__ == "__main__":
    sys.exit(main())
