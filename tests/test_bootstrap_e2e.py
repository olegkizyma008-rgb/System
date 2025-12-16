import os
import subprocess
from pathlib import Path


def _run(cmd, *, cwd: Path, env: dict) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Command failed: {cmd}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    return proc


def test_bootstrap_e2e(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "templates" / "bootstrap_new_project.sh"
    assert script.exists()

    parent_dir = tmp_path / "projects"
    parent_dir.mkdir(parents=True, exist_ok=True)

    project_name = "E2ETrinityProject"
    project_dir = parent_dir / project_name

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    windsurf_log = tmp_path / "windsurf_args.txt"
    fake_windsurf = bin_dir / "windsurf"
    fake_windsurf.write_text(
        "#!/bin/bash\n"
        f"LOG=\"{windsurf_log}\"\n"
        "rm -f \"$LOG\" 2>/dev/null || true\n"
        "for a in \"$@\"; do\n"
        "  echo \"$a\" >> \"$LOG\"\n"
        "done\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_windsurf.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env.setdefault("GIT_AUTHOR_NAME", "Trinity")
    env.setdefault("GIT_AUTHOR_EMAIL", "trinity@example.com")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])

    bootstrap = subprocess.run(
        ["bash", str(script), project_name, str(parent_dir)],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert bootstrap.returncode == 0, f"bootstrap failed\nstdout:\n{bootstrap.stdout}\nstderr:\n{bootstrap.stderr}"

    assert project_dir.is_dir()
    hook = project_dir / ".git" / "hooks" / "post-commit"
    assert hook.exists()
    assert os.access(str(hook), os.X_OK)

    assert windsurf_log.exists()
    args = windsurf_log.read_text(encoding="utf-8").splitlines()
    assert "--new-window" in args
    assert str(project_dir) in args

    (project_dir / "hello.txt").write_text("hello", encoding="utf-8")
    _run(["git", "add", "hello.txt"], cwd=project_dir, env=env)
    _run(["git", "commit", "-m", "test: trigger post-commit"], cwd=project_dir, env=env)

    structure = project_dir / "project_structure_final.txt"
    assert structure.exists()

    names = _run(
        ["git", "show", "--name-only", "--pretty=format:", "HEAD"],
        cwd=project_dir,
        env=env,
    ).stdout.splitlines()
    assert "hello.txt" in names
    assert "project_structure_final.txt" in names

    status = _run(["git", "status", "--porcelain"], cwd=project_dir, env=env).stdout.strip()
    assert status == ""
