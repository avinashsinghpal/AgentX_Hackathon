"""Migration-graph sanity checks (dialect independent)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

API_ROOT = Path(__file__).resolve().parent.parent


def _script_directory() -> ScriptDirectory:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def test_migration_graph_has_a_single_head() -> None:
    script = _script_directory()
    heads = script.get_heads()
    assert heads == ["e7f8a9b0c1d2"], heads


def test_applied_revisions_are_never_rewritten() -> None:
    script = _script_directory()
    revisions = {revision.revision: revision for revision in script.walk_revisions()}
    # The two pre-existing revisions must keep their identifiers and order so
    # databases already at head can upgrade incrementally.
    assert revisions["73fa33a3a744"].down_revision is None
    assert revisions["3d74bdde4fe4"].down_revision == "73fa33a3a744"
    assert revisions["9a1f0b6c4d21"].down_revision == "3d74bdde4fe4"
    assert revisions["c4b7e2d9a1f3"].down_revision == "9a1f0b6c4d21"


def test_every_revision_has_a_downgrade() -> None:
    script = _script_directory()
    for revision in script.walk_revisions():
        source = Path(revision.path).read_text(encoding="utf-8")
        assert "def downgrade()" in source, revision.revision
