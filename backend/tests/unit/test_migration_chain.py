"""마이그레이션 사슬 검사 — 한 줄로 이어지고, 파일 이름 번호와 실제 순서가 일치하는가.

Alembic 은 파일 이름이 아니라 각 파일의 `down_revision` 사슬로 순서를 정한다. 두 사람이 같은 번호를 만들어
머지하거나, 번호만 고치고 `down_revision` 을 그대로 두면 사슬과 번호가 어긋난다. 그 상태를 DB 없이 파일만 읽어 잡는다.
충돌 해결 규칙은 docs/development/collaboration.md 「충돌을 막는 규칙」.
"""

from pathlib import Path

import pytest
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[2]


def migration_chain_problems(scripts: ScriptDirectory) -> list[str]:
    heads = scripts.get_heads()
    if len(heads) > 1:
        return [
            f"마이그레이션 사슬이 갈라졌다(끝이 {len(heads)}개: {sorted(heads)}) — 뒤에 머지한 쪽이 번호와 down_revision 을 고친다"
        ]

    problems: list[str] = []
    # walk_revisions 는 끝(head) → 처음(base) 순서라 뒤집는다
    chain = list(reversed(list(scripts.walk_revisions())))
    for index, script in enumerate(chain, start=1):
        expected = f"{index:04d}"
        name = Path(script.path).name
        if script.revision != expected:
            problems.append(f"{name}: 사슬의 {index}번째인데 revision 이 {script.revision!r} 이다(기대 {expected!r})")
        if not name.startswith(f"{script.revision}_"):
            problems.append(f"{name}: 파일 이름 번호가 revision {script.revision!r} 과 다르다")
    return problems


def test_repository_migration_chain() -> None:
    scripts = ScriptDirectory(str(BACKEND_DIR / "migrations"))

    assert migration_chain_problems(scripts) == []


# ---------- 검사기 자체가 어긋남을 잡는지 ----------


def _scripts(tmp_path: Path, files: dict[str, tuple[str, str | None]]) -> ScriptDirectory:
    """{파일 이름: (revision, down_revision)} 으로 임시 마이그레이션 폴더를 만든다."""
    versions = tmp_path / "versions"
    versions.mkdir()
    for name, (revision, down_revision) in files.items():
        (versions / name).write_text(f"revision = {revision!r}\ndown_revision = {down_revision!r}\n")
    return ScriptDirectory(str(tmp_path), version_locations=[str(versions)])


def test_linear_numbered_chain_passes(tmp_path: Path) -> None:
    scripts = _scripts(tmp_path, {"0001_a.py": ("0001", None), "0002_b.py": ("0002", "0001")})

    assert migration_chain_problems(scripts) == []


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        pytest.param(
            {"0001_a.py": ("0001", None), "0002_b.py": ("0002", "0001"), "0002_c.py": ("0002x", "0001")},
            "갈라졌다",
            id="branched-same-slot",
        ),
        pytest.param(
            {"0001_a.py": ("0001", None), "0003_b.py": ("0003", "0001")},
            "2번째인데",
            id="skipped-number",
        ),
        pytest.param(
            {"0001_a.py": ("0001", None), "0003_b.py": ("0002", "0001")},
            "파일 이름 번호",
            id="filename-revision-mismatch",
        ),
        pytest.param(
            {"0001_a.py": ("0001", None), "0002_b.py": ("0002", "0003"), "0003_c.py": ("0003", "0001")},
            "2번째인데",
            id="renumbered-without-down-revision",
        ),
    ],
)
def test_broken_chain_is_reported(tmp_path: Path, files: dict[str, tuple[str, str | None]], expected: str) -> None:
    problems = migration_chain_problems(_scripts(tmp_path, files))

    assert any(expected in problem for problem in problems), problems
