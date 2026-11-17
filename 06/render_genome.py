"""Export any saved run without rerunning optimization."""
from pathlib import Path
import argparse
import json
import numpy as np
from PIL import Image
from triangle_ga import Genome, render


def export_svg(run, path: Path):
    def color(rgb):
        return "rgb(" + ",".join(str(int(round(x))) for x in rgb) + ")"
    lines=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">',
           '<rect width="64" height="64" fill="'+color(run['background'])+'"/>']
    for gene in run['genome']:
        xy=" ".join(f"{gene[i]:.3f},{gene[i+1]:.3f}" for i in [0,2,4])
        lines.append('<polygon points="'+xy+'" fill="'+color(gene[6:])+'"/>')
    lines.append('</svg>')
    path.write_text("\n".join(lines),encoding="utf-8")


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    run=json.loads(args.run.read_text())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    image=render(Genome(np.array(run['genome'])),64,np.array(run['background']))
    Image.fromarray(np.rint(image*255).astype(np.uint8)).save(args.out.with_suffix('.png'))
    export_svg(run,args.out.with_suffix('.svg'))
