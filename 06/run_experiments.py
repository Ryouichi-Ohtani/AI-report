"""Run all declared experiments and regenerate figures from saved raw JSON."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import platform
import sys

import numpy as np
import PIL
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from triangle_ga import evolve, metrics, save_run, Genome, render
from targets import TARGETS, add_noise

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
CONFIGS = {
    "mae08": dict(kind="mae",count=8),
    "mae24": dict(kind="mae",count=24),
    "mae48": dict(kind="mae",count=48),
    "mse24": dict(kind="mse",count=24),
    "perceptual24": dict(kind="perceptual",count=24),
    "variable": dict(kind="perceptual",count=12,variable=True,penalty=.0007),
}
COLORS = ["#23606e", "#d46b4d", "#629c77", "#c3943c", "#795d98", "#cf547b"]


def run(evaluations=12000, seeds=5):
    RESULTS.mkdir(parents=True, exist_ok=True)
    originals = {}
    for name, generator in TARGETS.items():
        clean = generator(64)
        originals[name] = clean
        Image.fromarray(clean).save(RESULTS / (name + "_original.png"))
        Image.fromarray(add_noise(clean)).save(RESULTS / (name + "_noisy.png"))
        Image.fromarray(generator(64,related=True)).save(RESULTS / (name + "_related.png"))
    configurations = [(t, noise, config, params) for t in TARGETS
                      for noise in (False,True) for config,params in CONFIGS.items()]
    configurations += [("landscape", False, "population04",dict(kind="mae",count=24,population=4)),
                       ("landscape", False, "population36",dict(kind="mae",count=24,population=36)),
                       ("landscape", False, "unguided",dict(kind="mae",count=24,guided=False)),
                       ("landscape", False, "variable_unpenalized",dict(kind="perceptual",count=12,variable=True,penalty=0)),
                       ("landscape", False, "variable_sparse",dict(kind="perceptual",count=12,variable=True,penalty=.0015))]
    total = len(configurations)*seeds
    done = 0
    for target, noisy, config, params in configurations:
        for seed in range(seeds):
            run_id = f"{target}_{'noisy' if noisy else 'clean'}_{config}_{seed}"
            path = RESULTS / "runs" / (run_id + ".json")
            if path.exists():
                done += 1
                continue
            clean = originals[target]
            train = add_noise(clean) if noisy else clean
            result = evolve(train,seed=seed,evaluations=evaluations,**params)
            result.update(target=target, noisy=noisy, config=config,
                          train_sha256=hashlib.sha256(train.tobytes()).hexdigest())
            result["train_metrics"] = metrics(result["image"],train)
            result["clean_metrics"] = metrics(result["image"],clean)
            result["noisy_test_metrics"] = metrics(result["image"],add_noise(clean,seed=918211))
            related = TARGETS[target](64,related=True)
            result["related_metrics"] = metrics(result["image"],related)
            other = list(TARGETS)[(list(TARGETS).index(target)+1)%len(TARGETS)]
            result["unrelated_metrics"] = metrics(result["image"],originals[other])
            save_run(result,path)
            if seed == 0:
                Image.fromarray(np.rint(result["image"]*255).astype(np.uint8)).save(RESULTS/(run_id+".png"))
                if target == "landscape" and noisy and config == "mae24":
                    for step,image in result["snapshots"].items():
                        Image.fromarray(np.rint(image*255).astype(np.uint8)).save(RESULTS/("evolution_"+step+".png"))
            done += 1
            print(f"{done}/{total} {run_id} cleanMAE={result['clean_metrics']['mae']:.4f} n={result['count']} {result['seconds']:.2f}s",flush=True)
    metadata = {"python":sys.version,"platform":platform.platform(),"numpy":np.__version__,
                "pillow":PIL.__version__,"matplotlib":matplotlib.__version__,
                "evaluations_per_run":evaluations,"seeds":list(range(seeds)),
                "size":64,"train_noise_sigma_255":22,"train_noise_seed":20261117,
                "test_noise_seed":918211,"run_count":total,
                "notes":"Runtime is wall time under concurrent experiments; all test references remain outside evolve()."}
    (RESULTS/"metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")


def load():
    return [json.loads(path.read_text()) for path in sorted((RESULTS/"runs").glob("*.json"))]


def plot():
    data=load()
    plt.rcParams.update({"font.size":9,"axes.spines.top":False,"axes.spines.right":False,
                         "figure.dpi":140,"savefig.bbox":"tight","font.family":"DejaVu Sans"})
    def select(target="landscape",noise=True,config="mae24"):
        return [r for r in data if r["target"]==target and r["noisy"]==noise and r["config"]==config]
    def raster(run):
        return render(Genome(np.array(run["genome"])),64,np.array(run["background"]))
    fig,axes=plt.subplots(3,6,figsize=(11.5,6.4))
    headings=["Clean reference", "Noisy training", "24: MSE", "24: MAE", "24: perceptual", "Variable length"]
    for row,target in enumerate(TARGETS):
        originals=[TARGETS[target](64),add_noise(TARGETS[target](64))]
        for col in range(6):
            ax=axes[row,col]
            if col<2:
                ax.imshow(originals[col]); label=target if col==0 else "sigma=22/255"
            else:
                config=["mse24","mae24","perceptual24","variable"][col-2]
                r=select(target,True,config)[0]
                ax.imshow(raster(r)); label=f"n={r['count']}; clean MAE={r['clean_metrics']['mae']:.3f}"
            ax.set_xlabel(label,fontsize=8)
            ax.set_xticks([]); ax.set_yticks([])
            if row==0: ax.set_title(headings[col],fontsize=9)
    fig.tight_layout(); fig.savefig(RESULTS/"reconstructions.pdf"); fig.savefig(RESULTS/"reconstructions.png"); plt.close(fig)

    fig,axes=plt.subplots(3,1,figsize=(4.2,6.6))
    for ax,target in zip(axes,TARGETS):
        for noisy,color in [(False,COLORS[0]),(True,COLORS[1])]:
            means=[]; deviations=[]
            for config in ["mae08","mae24","mae48"]:
                values=[r["clean_metrics"]["mae"] for r in select(target,noisy,config)]
                means.append(np.mean(values)); deviations.append(np.std(values,ddof=1))
            ax.errorbar([8,24,48],means,yerr=deviations,marker="o",capsize=3,color=color,label="Noisy train" if noisy else "Clean train")
        ax.set(title=target,xlabel="Triangle count",ylabel="Clean-reference MAE"); ax.set_xticks([8,24,48]); ax.grid(alpha=.2)
    axes[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(RESULTS/"complexity.pdf"); fig.savefig(RESULTS/"complexity.png"); plt.close(fig)

    fig,axes=plt.subplots(3,1,figsize=(4.2,6.6))
    for ax,target in zip(axes,TARGETS):
        configs=["mse24","mae24","perceptual24"]
        for index,(key,label) in enumerate([("mae","Clean MAE"),("edge_mae","Clean edge MAE")]):
            xs=np.arange(3)+index*.35
            means=[np.mean([r["clean_metrics"][key] for r in select(target,True,c)]) for c in configs]
            stds=[np.std([r["clean_metrics"][key] for r in select(target,True,c)],ddof=1) for c in configs]
            ax.bar(xs,means,width=.32,yerr=stds,capsize=3,label=label,color=COLORS[index])
        ax.set_xticks(np.arange(3)+.175); ax.set_xticklabels(["MSE","MAE","Perceptual"]); ax.set_title(target)
        ax.set_ylabel("Error in [0,1] RGB"); ax.grid(axis="y",alpha=.2)
    axes[0].legend(fontsize=8);fig.tight_layout();fig.savefig(RESULTS/"objectives.pdf");fig.savefig(RESULTS/"objectives.png");plt.close(fig)

    fig,axes=plt.subplots(2,1,figsize=(4.2,5.2))
    for color,config in zip(COLORS,CONFIGS):
        runs=select("landscape",True,config)
        values=np.array([[p["loss"]/r["trace"][0]["loss"] for p in r["trace"]] for r in runs])
        xs=[p["evaluations"] for p in runs[0]["trace"]]
        q1,med,q3=np.percentile(values,[25,50,75],axis=0)
        axes[0].plot(xs,med,color=color,label=config)
        axes[0].fill_between(xs,q1,q3,color=color,alpha=.12)
    axes[0].set(xlabel="Rendered candidates",ylabel="Training objective / initial",title="Noisy landscape; median and IQR")
    axes[0].legend(fontsize=7,ncol=2);axes[0].grid(alpha=.2)
    for color,config in zip(COLORS,["variable_unpenalized","variable","variable_sparse"]):
        runs=select("landscape",False,config)
        axes[1].scatter([r["count"] for r in runs],[r["clean_metrics"]["mae"] for r in runs],label=f"lambda={runs[0]['penalty']}",color=color,s=30)
    axes[1].set(xlabel="Evolved triangle count",ylabel="Clean MAE",title="Complexity penalty; all 5 seeds")
    axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    fig.tight_layout();fig.savefig(RESULTS/"evolution_pareto.pdf");fig.savefig(RESULTS/"evolution_pareto.png");plt.close(fig)

    fig,axes=plt.subplots(1,5,figsize=(10.5,2.5))
    for ax,name,title in zip(axes,["initial","3000","6000","final"],["Initial","3,000 renders","6,000 renders","12,000 renders"]):
        path=RESULTS/("evolution_"+name+".png")
        ax.imshow(Image.open(path));ax.set_title(title,fontsize=9);ax.axis("off")
    ax=axes[-1];ax.imshow(TARGETS["landscape"](64));ax.set_title("Clean test",fontsize=9);ax.axis("off")
    fig.tight_layout();fig.savefig(RESULTS/"progression.pdf");fig.savefig(RESULTS/"progression.png");plt.close(fig)

    summary=[]
    for target in TARGETS:
        for noisy in [False,True]:
            for config in CONFIGS:
                runs=select(target,noisy,config)
                record={"target":target,"noisy":noisy,"config":config,"runs":len(runs)}
                for key in ["count","seconds","loss","successful_crossovers","attempted_crossovers"]:
                    values=[r[key] for r in runs]
                    record[key+"_mean"]=float(np.mean(values));record[key+"_sd"]=float(np.std(values,ddof=1))
                for test in ["train_metrics","clean_metrics","noisy_test_metrics","related_metrics","unrelated_metrics"]:
                    for metric in ["mae","mse","psnr","edge_mae"]:
                        values=[r[test][metric] for r in runs]
                        record[test+"_"+metric+"_mean"]=float(np.mean(values));record[test+"_"+metric+"_sd"]=float(np.std(values,ddof=1))
                summary.append(record)
    with (RESULTS/"summary.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=summary[0].keys());writer.writeheader();writer.writerows(summary)
    (RESULTS/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    # Machine-generated LaTeX table: values never hand-copied into prose.
    lines=[r"\begin{tabular}{llrrr}",r"\toprule",r"画像 & 適合度 & $n$ & clean MAE & edge MAE \\",r"\midrule"]
    labels={"landscape":"風景","fruit":"果実","gradient":"勾配"}
    for target in TARGETS:
        for config,label in [("mse24","MSE"),("mae24","MAE"),("perceptual24","知覚代理"),("variable","可変長")]:
            s=next(x for x in summary if x["target"]==target and x["noisy"] and x["config"]==config)
            lines.append(f"{labels[target]} & {label} & {s['count_mean']:.1f} & {s['clean_metrics_mae_mean']:.3f} & {s['clean_metrics_edge_mae_mean']:.3f}" + r" \\")
        lines.append(r"\midrule")
    lines[-1]=r"\bottomrule";lines.append(r"\end{tabular}")
    (RESULTS/"table.tex").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"runs":len(data),"seconds":sum(r["seconds"] for r in data)},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--plot-only",action="store_true")
    parser.add_argument("--evaluations",type=int,default=12000)
    parser.add_argument("--seeds",type=int,default=5)
    args=parser.parse_args()
    if not args.plot_only: run(args.evaluations,args.seeds)
    plot()
