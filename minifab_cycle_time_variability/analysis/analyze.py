"""Replicated contrasts, ANOVA, Shapley attribution, budget and publication figures."""
from pathlib import Path
import json,itertools,math,sqlite3
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'results';FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'savefig.bbox':'tight'})
COLORS=['#243b53','#ef8354','#2a9d8f','#9b5de5','#dca11d','#006d77']
LABELS={'Baseline':'Baseline','A':'A: partial batches','B':'B: litho setups','C':'C: implant repair','D':'D: smooth releases','ABCD':'All improvements'}
def ci(x):
    x=np.asarray(x,dtype=float);return stats.t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x)) if len(x)>1 else np.nan
def save(name):
    plt.savefig(FIG/(name+'.png'));plt.savefig(FIG/(name+'.svg'));plt.close()
def analyze():
    runs=pd.read_csv(DATA/'runs.csv');runs['hours']=runs.mean_ct/60
    summ=[]
    for (view,load,scenario),g in runs.groupby(['view','load','scenario']):
        row=dict(view=view,load=load,scenario=scenario,n=len(g),mean_hours=g.hours.mean(),halfwidth=ci(g.hours),
            relative_halfwidth=ci(g.hours)/g.hours.mean(),sd_hours=g.sd_ct.mean()/60,p95_hours=g.p95_ct.mean()/60,
            throughput=g.throughput_day.mean(),wip=g.wip.mean(),util=g.litho_util.mean(),
            analytic_util=g.litho_analytic_util.mean(),fill=g.batch_fill.mean(),x_factor=g.x_factor.mean(),
            setups_day=g.setups_day.mean(),litho_pm=g.Me_pm.mean(),litho_repair=g.Me_repair.mean(),
            implant_repair=(g.Mc_repair.mean()+g.Md_repair.mean())/2,
            ll_max=float(g.little_relative_error.abs().max()))
        row['precision_pass']=row['relative_halfwidth']<.05
        summ.append(row)
    summary=pd.DataFrame(summ);summary.to_csv(DATA/'summary.csv',index=False)
    effects=[];shap=[];anova=[];diagnostics=[]
    terms=list('ABCD')+[''.join(t) for t in itertools.combinations('ABCD',2)]
    for (view,load),g in runs.groupby(['view','load']):
        for term in terms:
            vals=[]
            for rep,rr in g.groupby('rep'):
                sign=np.prod([2*rr[f].to_numpy()-1 for f in term],axis=0)
                vals.append(float(np.sum(sign*rr.hours)/8))
            mean=np.mean(vals);hw=ci(vals);se=np.std(vals,ddof=1)/np.sqrt(len(vals))
            p=2*stats.t.sf(abs(mean/se),len(vals)-1) if se else 0.
            effects.append(dict(view=view,load=load,term=term,effect_hours=mean,halfwidth=hw,p_value=p,
                difference_in_differences=2*mean if len(term)==2 else np.nan))
        # Shapley gains: baseline minus all; allocate interactions across factors fairly.
        for factor in 'ABCD':
            vals=[]
            for rep,rr in g.groupby('rep'):
                values={frozenset(k for k in 'ABCD' if row[k]):row['hours'] for row in rr.to_dict('records')}
                others=set('ABCD')-{factor};value=0
                for size in range(4):
                    for subset in itertools.combinations(others,size):
                        s=frozenset(subset);w=math.factorial(size)*math.factorial(3-size)/math.factorial(4)
                        value+=w*(values[s]-values[s|{factor}])
                vals.append(value)
            shap.append(dict(view=view,load=load,factor=factor,hours_saved=np.mean(vals),halfwidth=ci(vals)))
        gg=g.copy()
        for factor in 'ABCD':gg['x'+factor]=2*gg[factor]-1
        for scale in ['raw','log']:
            gg['response']=gg.hours if scale=='raw' else np.log(gg.hours)
            formula='response ~ C(rep) + (xA+xB+xC+xD)**2'
            fit=ols(formula,gg.drop(columns=['C'])).fit()
            tab=sm.stats.anova_lm(fit,typ=2).reset_index().rename(columns={'index':'term'})
            tab['view']=view;tab['load']=load;tab['scale']=scale;anova.append(tab)
            sh=stats.shapiro(fit.resid);lev=stats.levene(*[x.response.to_numpy() for _,x in gg.groupby('scenario')])
            diagnostics.append(dict(view=view,load=load,scale=scale,shapiro_p=sh.pvalue,levene_p=lev.pvalue,r_squared=fit.rsquared,
                caveat='ANOVA p-values descriptive under CRN; paired contrast t-tests primary; no multiplicity correction'))
            if view=='equal_starts' and load==.85:
                fig,ax=plt.subplots(1,2,figsize=(10,3.4));ax[0].scatter(fit.fittedvalues,fit.resid,c=COLORS[2]);ax[0].axhline(0,c='gray',lw=1)
                ax[0].set(xlabel='Fitted '+scale+' response',ylabel='Residual');sm.qqplot(fit.resid,line='s',ax=ax[1]);fig.suptitle('85% baseline-load experiment: '+scale+' residual checks');save('residuals_'+scale)
    ef=pd.DataFrame(effects);ef.to_csv(DATA/'effects.csv',index=False)
    sp=pd.DataFrame(shap);sp.to_csv(DATA/'shapley.csv',index=False)
    pd.concat(anova).to_csv(DATA/'anova.csv',index=False);pd.DataFrame(diagnostics).to_csv(DATA/'residual_diagnostics.csv',index=False)
    for view in ['equal_starts','equal_utilization']:
        fig,ax=plt.subplots(figsize=(9,5.1))
        for color,scenario in zip(COLORS,LABELS):
            g=summary[(summary.view==view)&(summary.scenario==scenario)].sort_values('load')
            ax.errorbar(g.throughput,g.mean_hours,yerr=g.halfwidth,marker='o',capsize=3,label=LABELS[scenario],color=color)
        ax.set(xlabel='Measured throughput (lots/day)',ylabel='Mean cycle time (hours)',title='Operating curves | '+view.replace('_',' '));ax.grid(alpha=.15);ax.legend(fontsize=9,ncol=2);save('operating_'+view)
    p=sp[(sp.view=='equal_starts')&(sp.load==.85)].sort_values('hours_saved')
    fig,ax=plt.subplots(figsize=(9,4.5));ax.barh(p.factor,p.hours_saved,xerr=p.halfwidth,color=COLORS[2],capsize=4)
    ax.axvline(0,color='gray',lw=1);ax.set(xlabel='Hours saved: Shapley allocation, 95% paired CI',title='85% baseline load | attribution of baseline-to-all gain')
    interactions=ef[(ef.view=='equal_starts')&(ef.load==.85)&(ef.term.str.len()==2)]
    top=interactions.loc[interactions.effect_hours.abs().idxmax()]
    fig.subplots_adjust(bottom=.25)
    fig.text(.12,.025,f'Largest interaction: {top.term}; difference-in-differences {top.difference_in_differences:+.2f} h. Signed contributions, not physical delay shares.',fontsize=9);save('pareto_85')
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,load in zip(axes,[.7,.85,.95]):
        gg=ef[(ef.view=='equal_starts')&(ef.load==load)].sort_values('effect_hours')
        ax.barh(gg.term,gg.effect_hours,xerr=gg.halfwidth,color=COLORS[0],capsize=2);ax.axvline(0,c='gray',lw=1)
        ax.set(title=f'{load:.0%} baseline load',xlabel='Improved-minus-baseline effect (h)')
    fig.suptitle('Factorial effects and two-factor interactions');fig.tight_layout();save('effects')
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    g=runs[(runs.view=='equal_starts')&(runs.load==.85)]
    for ax,(f1,f2) in zip(axes.flat,itertools.combinations('ABCD',2)):
        for lev in [0,1]:
            v=g[g[f2]==lev].groupby(f1).hours.mean();ax.plot(v.index,v.values,'o-',label=f'{f2}={lev}')
        ax.set(xticks=[0,1],xlabel=f1,ylabel='Mean CT (h)',title=f'{f1} x {f2}');ax.legend()
    fig.tight_layout();save('interactions_85')
    # Cost model is deliberately editable and illustrative.
    costfile=ROOT/'costs.json'
    if not costfile.exists():costfile.write_text(json.dumps(dict(target_hours=24,costs={'A':1,'B':3,'C':5,'D':2},unit='illustrative relative cost units; not dollars'),indent=2))
    cost=json.loads(costfile.read_text());budget=[]
    base=g[g.scenario=='Baseline'].set_index('rep').hours
    for scenario,rr in g.groupby('scenario'):
        savings=base-rr.set_index('rep').hours
        row=summary[(summary.view=='equal_starts')&(summary.load==.85)&(summary.scenario==scenario)].iloc[0]
        expense=sum(cost['costs'][f] for f in 'ABCD' if scenario!='Baseline' and f in scenario)
        budget.append(dict(scenario=scenario,cost=expense,mean_hours=row.mean_hours,upper_95=row.mean_hours+row.halfwidth,
            saved_hours=savings.mean(),savings_halfwidth=ci(savings),meets_target=row.mean_hours<=cost['target_hours'],
            conservative_meets_target=row.mean_hours+row.halfwidth<=cost['target_hours']))
    budget=pd.DataFrame(budget).sort_values(['cost','mean_hours'])
    budget['pareto_efficient']=[not any((budget.cost<=row.cost)&(budget.mean_hours<=row.mean_hours)&((budget.cost<row.cost)|(budget.mean_hours<row.mean_hours))) for row in budget.itertuples()]
    budget.to_csv(DATA/'budget.csv',index=False)
    fig,ax=plt.subplots(figsize=(8,4.7));ax.scatter(budget.cost,budget.mean_hours,c=np.where(budget.pareto_efficient,COLORS[2],COLORS[0]),s=45)
    for row in budget.itertuples():ax.annotate(row.scenario,(row.cost,row.mean_hours),xytext=(4,4),textcoords='offset points',fontsize=8)
    ax.axhline(cost['target_hours'],c=COLORS[1],ls='--',label='Illustrative 24-hour target');ax.set(xlabel='Illustrative relative cost units',ylabel='Mean CT (hours)',title='Variability budget | 85% baseline load, equal starts');ax.legend();save('budget')
    # WIP Welch ensemble and window sensitivity.
    w=pd.read_csv(DATA/'warmup_samples.csv');fig,ax=plt.subplots(figsize=(9,4.5));warmrows=[]
    for color,load in zip(COLORS,[.7,.85,.95]):
        z=w[w.load==load].groupby('time').wip.mean();smooth=z.rolling(21,center=True,min_periods=10).mean()
        ax.plot(z.index/1440,smooth,label=f'{load:.0%}',c=color)
        for cut in [30,60,90,120]:
            vals=w[(w.load==load)&(w.time>=cut*1440)].groupby('rep').wip.mean()
            warmrows.append(dict(load=load,discard_days=cut,wip_mean=vals.mean(),halfwidth=ci(vals)))
    ax.axvline(90,c='gray',ls='--',label='90-day warm-up');ax.set(xlabel='Days from empty',ylabel='WIP (21-day moving ensemble mean)',title='Independent-pilot Welch plot');ax.legend();save('warmup_welch')
    pd.DataFrame(warmrows).to_csv(DATA/'warmup_sensitivity.csv',index=False)
    theory=pd.read_csv(DATA/'theory.csv');th=theory[(theory.view=='equal_starts')&(theory.scenario=='Baseline')]
    tt=th.groupby(['load','station'])[['ca2','ce2','te','u','naive_vut','multiserver_vut','observed_queue','estimated_queue','error_pct','batch_formation_observed','batch_formation_renewal']].mean().reset_index();tt.to_csv(DATA/'theory_baseline.csv',index=False)
    fig,ax=plt.subplots(figsize=(8,4.5))
    for st,color in zip(['Diffusion','Implant','Lithography'],COLORS):
        z=tt[tt.station==st];ax.plot(z.observed_queue/60,z.estimated_queue/60,'o-',label=st,c=color)
    lim=max(tt.observed_queue.max(),tt.estimated_queue.max())/60;ax.plot([0,lim],[0,lim],'--',c='gray');ax.set(xlabel='Simulated queue time per visit (h)',ylabel='Approximation (h)',title='Theory check | baseline');ax.legend();save('theory')
    gate=dict(runs=len(runs),all_precision_pass=bool(summary.precision_pass.all()),max_relative_halfwidth=float(summary.relative_halfwidth.max()),
        max_little_error=float(runs.little_relative_error.abs().max()),max_step_wip_identity_error=float((runs[[f'wip_step_{s}' for s in range(1,7)]].sum(axis=1)-runs.wip).abs().max()),
        max_util_target_error_equal_util=float((summary[summary.view=='equal_utilization'].util-summary[summary.view=='equal_utilization'].load).abs().max()),
        max_flow_imbalance=float(((runs.released-runs.completed)/runs.completed).abs().max()))
    (DATA/'validation.json').write_text(json.dumps(gate,indent=2));print(json.dumps(gate,indent=2))
    with sqlite3.connect(DATA/'reporting.sqlite') as db:
        for name,tab in [('runs',runs),('summary',summary),('effects',ef),('budget',budget),('theory',theory)]:tab.to_sql(name,db,if_exists='replace',index=False)
    if (DATA/'extras.csv').exists():
        x=pd.read_csv(DATA/'extras.csv');x['hours']=x.mean_ct/60
        out=x.groupby('case').agg(mean_hours=('hours','mean'),halfwidth=('hours',ci),wip=('wip','mean'),throughput=('throughput_day','mean'),fill=('batch_fill','mean')).reset_index();out.to_csv(DATA/'sensitivity_summary.csv',index=False)
        fig,ax=plt.subplots(figsize=(10,5));ax.barh(out.case,out.mean_hours,xerr=out.halfwidth,color=COLORS[2],capsize=3);ax.axvline(24,c=COLORS[1],ls='--');ax.set(xlabel='Mean CT (hours)',title='One-factor sensitivity and product-mix extensions');save('sensitivity')
    return summary,budget,sp,ef,gate
if __name__=='__main__':analyze()
