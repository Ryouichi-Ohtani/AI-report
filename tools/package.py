"""Package only public source and experiment artifacts; exclude personal metadata."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP = ['README.md', 'requirements.txt', '.gitignore', 'report.tex', 'report-support.sty', 'repository.tex', 'references.tex']
DIRECTORIES = ['01', '02', '03', '04', '05', '06', 'tools', '.github']


def main():
    files = [ROOT / name for name in TOP]
    for directory in DIRECTORIES:
        files += [p for p in (ROOT / directory).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix not in ['.pyc', '.DS_Store'] and p.name != '.DS_Store']
    destination = ROOT / 'output/ai-course-report-source.zip'
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, 'AI-report/' + str(path.relative_to(ROOT)))
    print(f'{len(files)} public files: {destination}')


if __name__ == '__main__':
    main()
