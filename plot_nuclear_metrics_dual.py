import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import sem       

df = pd.read_csv("image_summary.csv")

def agg_and_plot(sub, title, outfile):
    # Collapse: mean per seedling → mean ± SEM per condition
    sub_agg = (sub
               .groupby(["region", "genotype", "seedling"], as_index=False)
               .agg(intensity = ("integrated_intensity", "mean"),
                    area      = ("total_area", "mean")))
    bar     = (sub_agg
               .groupby(["region", "genotype"], as_index=False)
               .agg(intensity_mean = ("intensity", "mean"),
                    intensity_sem  = ("intensity", sem),
                    area_mean      = ("area",      "mean"),
                    area_sem       = ("area",      sem)))

    melted = bar.melt(id_vars=["region", "genotype"],
                      value_vars=["intensity_mean", "area_mean"],
                      var_name="metric", value_name="value")

    sns.set(style="whitegrid", font_scale=1.1)
    g = sns.catplot(
        data=melted, kind="bar",
        x="region", y="value", hue="genotype", col="metric",
        palette={"control": "#8ecae6", "mutant": "#ffb703"},
        errorbar=None,            
        height=4, aspect=0.9,     
        sharey=False, edgecolor="0.2"
    )


    # Add error bars manually (since we already computed SEM)
    for ax, metric in zip(g.axes.flat, ["intensity_mean", "area_mean"]):
        for i, region in enumerate(bar["region"].unique()):
            for j, genotype in enumerate(["control", "mutant"]):
                sem_val = bar.loc[
                    (bar["region"]==region)&(bar["genotype"]==genotype),
                    metric.replace("_mean","_sem")
                ].values
                if sem_val.size:
                    ax.errorbar(
                        i + j*0.2 - 0.1,      # x‑coord (matches dodge)
                        bar.loc[
                            (bar["region"]==region) & (bar["genotype"]==genotype),
                            metric
                        ].values,
                        yerr=sem_val,
                        fmt="none", ecolor="0.2", capsize=4, linewidth=1
                    )

    title_map = {"intensity_mean": "Integrated intensity",
                "area_mean":      "Integrated area"}

    for ax in g.axes.flat:
        raw = ax.get_title()                 # e.g. "metric = intensity_mean"
        metric_name = raw.split(" = ")[-1]   # → "intensity_mean"
        ax.set_title(title_map.get(metric_name, metric_name))


    g.set_axis_labels("", "")
    for ax, ylab in zip(g.axes.flat,
                        ["Integrated intensity (a.u.)", "Integrated area (px²)"]):
        ax.set_ylabel(ylab)
    g.fig.suptitle(title, y=1.05, fontsize=14)
    g.tight_layout()
    g.savefig(outfile, dpi=300)
    plt.close(g.fig)

# 1) z‑slices
agg_and_plot(df[df["zslice"].notna()],
             "Per-z-slice averages (biological replicates = individual seedlings)",
             "bar_zslices.png")

# 2) stitched stacks
agg_and_plot(df[df["zslice"].isna()],
             "Stitched / maximum-projection images",
             "bar_stacks.png")

print("✅  Two figures written:  bar_zslices.png  &  bar_stacks.png")
