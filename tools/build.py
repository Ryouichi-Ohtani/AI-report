"""Build the Japanese two-column report with Tectonic (macOS fonts by default)."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='use only cached Tectonic resources')
    args = parser.parse_args()
    out = ROOT / 'output/pdf'; out.mkdir(parents=True, exist_ok=True)
    # Matplotlib ships the BaKoMa CM extension font. Prepare an ignored private
    # format fallback when an offline TeX cache lacks its Type1 font.
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
    import matplotlib
    from prepare_math_font import prepare
    font = Path(matplotlib.get_data_path()) / 'fonts/ttf/cmex10.ttf'
    if font.exists():
        prepare(font, ROOT / 'report-cmex.pfb')
    command = ['tectonic', '--keep-logs', '--outdir', str(out), 'report.tex']
    if args.offline:
        command.insert(1, '-C')
    subprocess.run(command, cwd=ROOT, check=True)
    print(out / 'report.pdf')


if __name__ == '__main__':
    main()
