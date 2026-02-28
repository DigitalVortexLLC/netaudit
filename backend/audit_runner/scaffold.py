"""
Scaffold generator for audit runs.

Creates a temporary directory with pytest test files, configuration data,
and rules definitions used to execute an audit against a device config.
"""

import json
import shutil
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    keep_trailing_newline=True,
)


def create_scaffold(audit_run, config_text, simple_rules, custom_rules):
    """
    Build a temporary pytest project directory for an audit run.

    Parameters
    ----------
    audit_run : AuditRun
        The audit run instance (used for its ``id`` in the temp dir name).
    config_text : str
        Raw device configuration text to audit.
    simple_rules : list[dict]
        Each dict must have keys: id, name, rule_type, pattern, severity.
    custom_rules : list[dict]
        Each dict must have keys: filename, content.

    Returns
    -------
    pathlib.Path
        Path to the created temporary directory.
    """
    scaffold_path = Path(
        tempfile.mkdtemp(prefix=f"netaudit_{audit_run.id}_")
    )

    # Write the device configuration text
    (scaffold_path / "_config.txt").write_text(config_text)

    # Write the simple rules as JSON
    (scaffold_path / "_rules.json").write_text(
        json.dumps(simple_rules, indent=2)
    )

    # Render and write the root conftest.py
    conftest_template = _env.get_template("conftest.py.j2")
    (scaffold_path / "conftest.py").write_text(conftest_template.render())

    # Render and write the parametrized test file (only if rules exist)
    if simple_rules:
        test_template = _env.get_template("test_simple_rules.py.j2")
        (scaffold_path / "test_simple_rules.py").write_text(
            test_template.render()
        )

    # Create the custom/ subdirectory for custom test files
    if custom_rules:
        custom_dir = scaffold_path / "custom"
        custom_dir.mkdir()

        # Render and write the custom conftest.py
        custom_conftest_template = _env.get_template("custom_conftest.py.j2")
        (custom_dir / "conftest.py").write_text(
            custom_conftest_template.render()
        )

        # Write each custom rule test file
        for rule in custom_rules:
            (custom_dir / rule["filename"]).write_text(rule["content"])

    return scaffold_path


def cleanup_scaffold(scaffold_path):
    """
    Remove a scaffold directory created by :func:`create_scaffold`.

    Parameters
    ----------
    scaffold_path : pathlib.Path
        Path returned by ``create_scaffold``.  If the path does not exist
        or cannot be removed, errors are silently ignored.
    """
    shutil.rmtree(scaffold_path, ignore_errors=True)
