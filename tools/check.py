"""Run invariant tests and audit report inputs without re-running long experiments."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = dict(os.environ, MPLCONFIGDIR=str(ROOT / '.cache/matplotlib'))
    for number in range(1, 7):
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', f'{number:02d}', '-p', 'test_*.py'],
                       cwd=ROOT, env=env, check=True)
    for path in ROOT.glob('0*/results/**/*.json'):
        json.loads(path.read_text(encoding='utf-8'))
    for number in range(1, 7):
        section = (ROOT / f'{number:02d}/section.tex').read_text()
        assert f'\\repolink{{{number:02d}}}' in section
    print('All invariant tests, result JSON files, and six section links passed.')


if __name__ == '__main__':
    main()
