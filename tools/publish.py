"""Publish the already reviewed code to the user's explicitly requested public repo."""
import base64
import json
from pathlib import Path
import subprocess

from package import TOP, DIRECTORIES

ROOT = Path(__file__).resolve().parents[1]
REPO = 'Ryouichi-Ohtani/AI-report'
URL = 'https://github.com/' + REPO


def run(*args, capture=False, check=True):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=capture, check=check)


def api(path):
    return json.loads(run('gh', 'api', path, capture=True).stdout)


def remote_info():
    response = run('gh', 'api', f'repos/{REPO}', capture=True, check=False)
    if response.returncode:
        try:
            missing = str(json.loads(response.stdout).get('status')) == '404'
        except (ValueError, AttributeError):
            missing = False
        if missing:
            return None
        raise SystemExit('GitHub repository lookup failed; stopped.\n' + response.stderr.strip())
    info = json.loads(response.stdout)
    if info.get('full_name') != REPO or info.get('html_url') != URL:
        raise SystemExit('GitHub returned a different repository; stopped.')
    if info.get('private') is not False:
        raise SystemExit('An existing non-public repository has this name; stopped without changing it.')
    return info


def placeholder_commit(info):
    """Accept only the known one-heading README, never arbitrary remote work."""
    if info.get('default_branch') != 'main':
        raise SystemExit('Existing repository must have a main default branch; stopped.')
    reference = api(f'repos/{REPO}/git/ref/heads/main')
    target = reference.get('object', {})
    if reference.get('ref') != 'refs/heads/main' or target.get('type') != 'commit':
        raise SystemExit('Cannot resolve the existing main commit; stopped.')
    sha = target.get('sha', '')
    if len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha):
        raise SystemExit('Invalid remote commit identifier; stopped.')
    files = api(f'repos/{REPO}/contents?ref={sha}')
    if (not isinstance(files, list) or len(files) != 1
            or files[0].get('path') != 'README.md' or files[0].get('type') != 'file'):
        raise SystemExit('Existing repository contains more than a placeholder README; stopped to preserve its files.')
    readme = api(f'repos/{REPO}/contents/README.md?ref={sha}')
    try:
        text = base64.b64decode(readme['content']).decode('utf-8').strip()
    except (KeyError, ValueError, UnicodeError):
        raise SystemExit('Cannot validate the existing README; stopped.')
    if readme.get('encoding') != 'base64' or text not in {'# -', '# AI-report'}:
        raise SystemExit('Existing README is not the known placeholder; stopped to preserve its content.')
    return sha


def validate_public_files():
    tracked = run('git', 'ls-files', '-z', capture=True).stdout.split('\0')
    private_names = {'author-local.tex', 'cmex10.ttf', 'report-cmex.pfb', '.DS_Store'}
    private_dirs = {'.cache', '.venv', 'tmp', 'output', '__pycache__'}
    for path in filter(None, tracked):
        parts = Path(path).parts
        allowed = path in TOP or parts[0] in DIRECTORIES
        forbidden = (any(p in private_dirs or p == '.env' or p.startswith('.env.') for p in parts)
                     or parts[-1] in private_names or path.endswith('.pyc'))
        if not allowed or forbidden:
            raise SystemExit(f'Unexpected or private tracked file found: {path}; stopped before push.')


def set_origin():
    remote = run('git', 'remote', 'get-url', 'origin', capture=True, check=False)
    if remote.returncode:
        run('git', 'remote', 'add', 'origin', URL + '.git')
    elif remote.stdout.strip() not in [URL + '.git', URL, 'git@github.com:' + REPO + '.git']:
        raise SystemExit('origin points to a different destination; stopped.')


def verify_publication():
    if remote_info() is None:
        raise SystemExit('Public repository is missing; publication flag unchanged.')
    remote = run('git', 'ls-remote', 'origin', 'refs/heads/main', capture=True).stdout.split()
    local_sha = run('git', 'rev-parse', 'HEAD', capture=True).stdout.strip()
    if not remote or remote[0] != local_sha:
        raise SystemExit('Remote main does not match local HEAD; publication not verified.')


def main():
    account = run('gh', 'api', 'user', '--jq', '.login', capture=True).stdout.strip()
    if account != 'Ryouichi-Ohtani':
        raise SystemExit('Expected authenticated GitHub account Ryouichi-Ohtani; no changes made.')
    fresh = not (ROOT / '.git').exists()
    info = remote_info()
    # Validate the immutable remote commit before creating local Git metadata.
    base = placeholder_commit(info) if fresh and info else None
    public_paths = TOP + DIRECTORIES
    if any(not (ROOT / path).exists() for path in public_paths):
        raise SystemExit('A required public source path is missing; stopped.')
    if fresh:
        run('git', 'init', '-b', 'main')
        run('git', 'config', 'user.name', 'Ryouichi Ohtani')
        run('git', 'config', 'user.email', 'Ryouichi-Ohtani@users.noreply.github.com')
        if base:
            set_origin()
            run('git', 'fetch', 'origin', 'main')
            fetched = run('git', 'rev-parse', 'refs/remotes/origin/main', capture=True).stdout.strip()
            if fetched != base:
                raise SystemExit('Remote main changed after inspection; stopped without staging local files.')
            # Only a newly initialized, unborn local branch reaches this line.
            # Mixed reset attaches its HEAD/index to the remote initial commit;
            # it leaves every local source file untouched and preserves history.
            run('git', 'reset', '--mixed', base)
        run('git', 'add', '--', *public_paths)
    elif run('git', 'status', '--porcelain', capture=True).stdout:
        raise SystemExit('Working tree must be clean. Review and commit changes before publishing.')
    if run('git', 'branch', '--show-current', capture=True).stdout.strip() != 'main':
        raise SystemExit('The local branch must be main; stopped.')
    validate_public_files()
    if fresh:
        run('git', 'commit', '-m', 'Add reproducible AI course experiments and two-column report sources')
    if info is None:
        # Check origin even for creation, so an unrelated remote is not replaced.
        remote = run('git', 'remote', 'get-url', 'origin', capture=True, check=False)
        if not remote.returncode:
            raise SystemExit('Local origin already exists but the target repository is missing; stopped.')
        run('gh', 'repo', 'create', REPO, '--public', '--source', '.', '--remote', 'origin', '--push')
    else:
        if info.get('default_branch') != 'main':
            raise SystemExit('Existing repository must have a main default branch; stopped.')
        set_origin()
        run('git', 'fetch', 'origin', 'main')
        ancestry = run('git', 'merge-base', '--is-ancestor', 'refs/remotes/origin/main', 'HEAD', check=False)
        if ancestry.returncode:
            raise SystemExit('Remote main is not an ancestor of local HEAD; stopped without merging or forcing a push.')
        run('git', 'push', '-u', 'origin', 'main')
    verify_publication()
    config = ROOT / 'repository.tex'
    text = config.read_text()
    if '\\repositorypublishedfalse' in text:
        config.write_text(text.replace('\\repositorypublishedfalse', '\\repositorypublishedtrue'))
        readme = ROOT / 'README.md'
        readme.write_text(readme.read_text().replace('GitHub公開は未確認です。', 'GitHub公開を確認済みです：' + URL + ' 。'))
        run('git', 'add', 'repository.tex')
        run('git', 'add', 'README.md')
        run('git', 'commit', '-m', 'Verify public source publication and activate report links')
        run('git', 'push', 'origin', 'main')
        verify_publication()
    print('Verified public repository: ' + URL)
    print('Rebuild the personal report: python3 tools/build.py --offline')


if __name__ == '__main__':
    main()
