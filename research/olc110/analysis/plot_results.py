"""Export the frozen OLC110 findings using ordinary scientific plotting."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
ARMS = json.loads((ROOT / "docs/EXPERIMENT_FREEZE.json").read_text())["arms"]
LABELS = {
    "BASE": "OLC109 originale",
    "STATIC_HALF": "50% investito / 50% cash",
    "STATIC_75": "75% investito / 25% cash",
    "REFRESH_WEEKLY": "Selettore settimanale",
    "EXIT21_MONTHLY": "Uscita 21 / rientro mensile",
    "EXIT21_SLOW": "Uscita 21 / rientro lento",
    "EXIT21_FAST": "Uscita 21 / rientro rapido",
    "EXIT21_STAGED": "Uscita 21 / rientro graduale",
    "EXIT63_STAGED": "Uscita 63 / rientro graduale",
    "TRAIL15_STAGED": "Trailing 15% / graduale",
    "VOLTRAIL_STAGED": "Trailing volatilità / graduale",
    "EXIT21_STAGED_FRESHW": "Nuove opportunità settimanali",
    "EXIT21_STAGED_FRESHD": "Nuove opportunità giornaliere",
}
COLORS = {"BASE": "#164f79", "STATIC_75": "#219177", "STATIC_HALF": "#79b9a6",
          "EXIT63_STAGED": "#a46d15", "EXIT21_STAGED_FRESHW": "#c63d55",
          "EXIT21_STAGED_FRESHD": "#8c598e"}
MAIN = ["BASE", "STATIC_75", "EXIT63_STAGED", "EXIT21_STAGED_FRESHW"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.labelcolor": "#314456",
                     "text.color": "#172b3a", "xtick.color": "#435564",
                     "ytick.color": "#435564", "savefig.facecolor": "white"})
score = pd.read_csv(ROOT / "results/SCORECARD.csv", float_precision="round_trip")
base = score[score.scenario == "BASE"].set_index("arm").loc[ARMS]
fig, axes = plt.subplots(2, 2, figsize=(16, 11.8), gridspec_kw={"height_ratios": [1, 1.1]})
fig.subplots_adjust(left=.075, right=.965, top=.80, bottom=.11, hspace=.42, wspace=.48)
fig.suptitle("OLC110 · Protezione, liquidità e rientro", x=.075, y=.975, ha="left", fontsize=23, fontweight="bold")
fig.text(.075, .938, "Nessuna delle nove protezioni dinamiche supera il controllo con il 25% in cash su CAGR e drawdown.", fontsize=13)
fig.text(.075, .909, "2 marzo 2020 – 30 ottobre 2026  •  2.096 ETF EUR Xetra  •  Scenario BASE con costi  •  Studio esplorativo", fontsize=10, color="#506372")

for arm in MAIN:
    daily = pd.read_csv(ROOT / f"results/{arm}__BASE/DAILY.csv.gz", parse_dates=["date"], float_precision="round_trip")
    axes[0, 0].plot(daily.date, daily.nav_close, color=COLORS[arm], lw=1.8)
    points = daily[["nav_open", "nav_close"]].to_numpy().reshape(-1)
    drawdown = (points / np.maximum.accumulate(points) - 1).reshape(-1, 2).min(axis=1)
    assert abs(drawdown.min() - base.loc[arm, "maxdd_sampled"]) < 1e-12
    axes[0, 1].plot(daily.date, 100 * drawdown, color=COLORS[arm], lw=1.2)
axes[0, 0].set_title("Capitale finale da €10.000", loc="left", pad=12)
axes[0, 0].set_yscale("log")
axes[0, 0].set_yticks([10000, 20000, 40000, 60000])
axes[0, 0].get_yaxis().set_major_formatter(FuncFormatter(lambda x, pos: f"€{x:,.0f}".replace(",", ".")))
axes[0, 0].set_ylim(7000, 80000)
axes[0, 0].set_ylabel("Scala logaritmica")
axes[0, 1].set_title("Drawdown campionato a Open e Close", loc="left", pad=12)
axes[0, 1].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:.0f}%"))
axes[0, 1].set_ylim(-55, 3)
for ax in axes[0]:
    ax.grid(alpha=.16)
    ax.margins(x=.01)

legend_labels = [f"{LABELS[a]}  ·  €{base.loc[a, 'end_equity']:,.0f}".replace(",", ".") for a in MAIN]
fig.legend([plt.Line2D([0], [0], color=COLORS[a], lw=2.6) for a in MAIN], legend_labels,
           loc="upper left", bbox_to_anchor=(.067, .888), ncol=2, frameon=False,
           columnspacing=2.5, fontsize=10)

ax = axes[1, 0]
position = ax.get_position()
ax.set_position([.205, position.y0, .30, position.height])
y = np.arange(len(ARMS))
vals = base.cagr.to_numpy() * 100
ax.barh(y, vals, color=[COLORS.get(a, "#aab6c0") for a in ARMS], height=.65)
ax.set_yticks(y, [LABELS[a] for a in ARMS], fontsize=8.7)
ax.invert_yaxis()
ax.set_xlim(0, 32.5)
ax.axvline(30, color="#526676", ls="--", lw=1)
for idx, value in enumerate(vals):
    ax.text(value + .3, idx, f"{value:.2f}%".replace(".", ","), va="center", fontsize=9)
ax.text(30, -.9, "Obiettivo 30%", ha="right", fontsize=9, color="#526676")
ax.set_title("Le 13 configurazioni · CAGR", loc="left", pad=18)
ax.set_xlabel("Rendimento composto annuo (%)")
ax.grid(axis="x", alpha=.15)
ax.set_axisbelow(True)

ax = axes[1, 1]
for arm in ARMS:
    ax.scatter(-100 * base.loc[arm, "maxdd_sampled"], 100 * base.loc[arm, "cagr"],
               s=100 if arm in COLORS else 42, color=COLORS.get(arm, "#aab6c0"),
               edgecolor="white", linewidth=.6, zorder=3)
annotations = {
    "BASE": (6, 7, "OLC109"),
    "STATIC_75": (-18, 10, "75% investito"),
    "STATIC_HALF": (7, -15, "50% investito"),
    "EXIT63_STAGED": (7, 5, "Uscita 63"),
    "EXIT21_STAGED_FRESHW": (-13, -23, "Opportunità settimanali"),
    "EXIT21_STAGED_FRESHD": (-15, 9, "Opportunità giornaliere"),
}
for arm, (dx, dy, label) in annotations.items():
    ax.annotate(label, (-100 * base.loc[arm, "maxdd_sampled"], 100 * base.loc[arm, "cagr"]),
                xytext=(dx, dy), textcoords="offset points", fontsize=9,
                ha="right" if dx < 0 else "left", color=COLORS[arm])
ax.set_title("Più rendimento, meno perdita massima", loc="left", pad=18)
ax.set_xlabel("Perdita massima campionata (%) · minore è meglio")
ax.set_ylabel("CAGR (%) · maggiore è meglio")
ax.set_xlim(21, 55)
ax.set_ylim(0, 30)
ax.grid(alpha=.15)
ax.text(.02, .97, "Zona preferibile: alto a sinistra", transform=ax.transAxes, va="top", fontsize=9, color="#526676")

fig.text(.075, .050, "Cash remunerato allo 0%; imposte escluse; unità frazionarie. Costi BASE: €1 + 15 bp per ordine. Nessuna leva di conto.", fontsize=9, color="#506372")
fig.text(.075, .030, "Il catalogo attuale e i prezzi di esecuzione hanno limiti storici e di capienza. Nessun holdout incontaminato; i risultati non certificano rendimenti futuri.", fontsize=9, color="#506372")
for extension in ["png", "svg"]:
    fig.savefig(OUT / f"OLC110_RISULTATI.{extension}", dpi=170)
plt.close(fig)
print("Exported figures/OLC110_RISULTATI.png and .svg; drawdowns reconciled with all four ledgers.")
