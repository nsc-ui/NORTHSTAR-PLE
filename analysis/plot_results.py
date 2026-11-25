"""Create report figures. Empty datasets produce clearly labeled placeholders, not results."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
figdir=ROOT/'figures'; figdir.mkdir(exist_ok=True)
sc=pd.read_csv(ROOT/'analysis'/'score_cost.csv')
fig,ax=plt.subplots(figsize=(7.2,4.8))
if len(sc) and {'model','score','cost_usd'}.issubset(sc.columns):
    for model,g in sc.groupby('model'):
        ax.plot(g['cost_usd'],g['score'],marker='o',label=model)
    ax.legend()
else:
    ax.text(.5,.5,'NO MEASUREMENTS YET\nRun the official 29-task dev evaluation\nand populate analysis/score_cost.csv',ha='center',va='center',transform=ax.transAxes)
ax.set(xlabel='Cost (USD)',ylabel='Dev-set score',title='Score vs. Cost (measured data only)'); ax.grid(True,alpha=.25)
fig.tight_layout(); fig.savefig(figdir/'score_vs_cost.png',dpi=180); plt.close(fig)
fc=pd.read_csv(ROOT/'analysis'/'failures.csv')
fig,ax=plt.subplots(figsize=(7.2,4.8))
if len(fc) and {'category','count'}.issubset(fc.columns):
    d=fc.sort_values('count',ascending=True); ax.barh(d['category'],d['count'])
else:
    ax.text(.5,.5,'NO FAILURE DATA YET\nClassify actual dev-run failures\nthen populate analysis/failures.csv',ha='center',va='center',transform=ax.transAxes)
ax.set(xlabel='Failure count',title='Failure Breakdown (observed failures only)')
fig.tight_layout(); fig.savefig(figdir/'failure_breakdown.png',dpi=180); plt.close(fig)
print('Generated report figure placeholders/plots. Empty datasets are explicitly marked.')
