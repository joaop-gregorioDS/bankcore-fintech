from pathlib import Path


MARKERS_BY_FILE = {
    "test_auth_jwt_hardening.py": ("security",),
    "test_data_privacy.py": ("unit", "security"),
    "test_demo_mode.py": ("unit",),
    "test_idempotency_ownership.py": ("unit",),
    "test_idempotency_postgres.py": ("integration", "postgres"),
    "test_migrations.py": ("unit",),
    "test_monetary_correctness.py": ("unit",),
    "test_p2f_risk_gate.py": ("integration", "postgres"),
}


def pytest_collection_modifyitems(items):
    for item in items:
        filename = Path(str(item.fspath)).name
        for marker in MARKERS_BY_FILE.get(filename, ()):
            item.add_marker(marker)
