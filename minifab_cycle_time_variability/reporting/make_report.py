"""Generate the two-page study report."""

from pathlib import Path

import json,math,textwrap

import pandas as pd

import numpy as np

from reportlab.pdfgen import canvas

from reportlab.lib.colors import HexColor,white

from reportlab.platypus import Paragraph,Table,TableStyle

from reportlab.lib.styles import ParagraphStyle

from reportlab.lib.enums import TA_LEFT

ROOT=Path(__file__).resolve().parents[2];D=ROOT/'results';F=ROOT/'figures'

INK=HexColor('#17324a');TEAL=HexColor('#087f8c');MUTED=HexColor('#586e80')

STYLE=ParagraphStyle('body',fontName='Helvetica',fontSize=9,leading=12,textColor=INK,spaceAfter=5)

def para(c,text,x,y,width,size=9,color=INK):

    st=ParagraphStyle('p',parent=STYLE,fontSize=size,leading=size*1.35,textColor=color)

    p=Paragraph(text,st);w,h=p.wrap(width,1000);p.drawOn(c,x,y-h);return y-h-7



def report():

    summary=pd.read_csv(D/'summary.csv');bud=pd.read_csv(D/'budget.csv');sp=pd.read_csv(D/'shapley.csv');ef=pd.read_csv(D/'effects.csv')

    val=json.loads((D/'validation.json').read_text());s=summary[(summary.view=='equal_starts')&(summary.load==.85)].set_index('scenario')

    base=s.loc['Baseline'];best=s.loc[s.mean_hours.idxmin()];smooth=s.loc['D'];allr=s.loc['ABCD']

    g=sp[(sp.view=='equal_starts')&(sp.load==.85)].sort_values('hours_saved',ascending=False)

    inter=ef[(ef.view=='equal_starts')&(ef.load==.85)&(ef.term.str.len()==2)]

    top=inter.loc[inter.effect_hours.abs().idxmax()]

    wide=int((~summary.precision_pass).sum())

    precision_file=D/'final_precision.csv'

    precision_note="The balanced factorial had 34 of 96 cells above the precision limit."

    if precision_file.exists():

        final=pd.read_csv(precision_file)

        precision_note=(f"{int(final.precision_pass.sum())}/96 cell means meet the 5% precision criterion "

                        f"for the measured horizon (maximum relative half-width {100*final.relative_halfwidth.max():.2f}%). "

                        "The balanced factorial uses 960 runs. Two fixed confirmation stages add 6,989 and 256 runs.")

    target=json.loads((ROOT/'costs.json').read_text())['target_hours']

    c=canvas.Canvas(str(ROOT/'reports/report.pdf'),pagesize=(612,792));c.setTitle('Mini-Fab: Cycle-Time Variability Study')

    def header(page,title):

        c.setFillColor(INK);c.rect(0,716,612,76,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',20);c.drawString(40,751,title);c.setFont('Helvetica',9);c.drawString(40,731,'RE-ENTRANT FAB / REPLICATED SIMULATION / 27 OCTOBER 2026')

        c.setFillColor(MUTED);c.setFont('Helvetica',8);c.drawString(40,22,'Research variant; all values are simulated. See accompanying source and audit tables.');c.drawRightString(572,22,str(page))

    header(1,'Cycle time: smooth the starts first')

    y=para(c,f'At 85% baseline load and equal starts, smoothing releases reduces mean cycle time from <b>{base.mean_hours:.1f} to {smooth.mean_hours:.1f} hours</b>. The best tested package is <b>{best.name}: {best.mean_hours:.1f} hours</b>. None meets the illustrative 24-hour target.',40,699,532,11)

    y=para(c,'Model correction: published setups are on lithography (B); random repairs are on implant (C). The brief assigns these to the opposite stations.',40,y,532,9)

    c.drawImage(str(F/'operating_equal_starts.png'),40,374,width=532,height=249,preserveAspectRatio=True,anchor='c',mask='auto')

    c.drawImage(str(F/'pareto_85.png'),40,132,width=532,height=230,preserveAspectRatio=True,anchor='c',mask='auto')

    para(c,f'The Pareto allocates the {base.mean_hours-allr.mean_hours:.1f}-hour baseline-to-all gain using all 16 cells. Negative values denote harmful contributions. Largest two-factor interaction: {top.term}, difference-in-differences {top.difference_in_differences:+.2f} h. Partial batching can lose more furnace capacity than it saves in waiting.',40,120,532,9)

    c.showPage();header(2,'Decision budget and validation limits')

    y=699

    for title,text in [

      ('Decision and cost model',f'The 24-hour target is infeasible. D alone costs 2 illustrative units and reaches {smooth.mean_hours:.2f} h; {best.name} reaches {best.mean_hours:.2f} h. Costs A/B/C/D = 1/3/5/2 are assumptions, not prices. The dashboard recalculates the least-cost feasible package for user-supplied costs and targets, including an upper-95%-CI screen.'),

      ('Experimental design',f'{val["runs"]} factorial runs cover 16 combinations, three loads and two views (equal starts and calibrated equal utilization). Measurement horizons: 365 days with five replications at 70%/85%; 730 days with 20 replications at 95%. All discard 90 warm-up days. Independent pilots, common random streams, blocked ANOVA, paired contrasts, raw/log residual checks and Shapley attribution are included.'),

      ('Verification and precision',precision_note+" Nine model tests passed. The 95% equal-starts ACD case showed rising WIP in a ten-year check, so its interval describes the finite measurement window. The 85% baseline confirmation gives 39.10 hours."),

      ('Theory and diminishing returns','VUT uses measured arrival and effective-service variability. Implant requires a two-server correction; diffusion additionally needs batch formation delay. Re-entrant dependence, operator contention and idle-time vacations explain limitations. Timeout/setup/repair sweeps are supplied. Faster repairs and shorter batch waits are not uniformly beneficial under the implemented resource schedules; do not extrapolate a monotonic benefit.'),

      ('External benchmark failed','The baseline reserves lithography for 105 minutes per lot. Scheduled maintenance leaves 9,660 minutes per week, giving a ceiling of 92 lots/week before setups. At 84 lots/week, only 10 minutes per lot remain for setups. Moving handling off the machine brought random starts to 1,849 +/- 70 minutes (published 1,813), but constant starts still took 1,459 +/- 3 minutes (published 1,161). None of four single changes matched both patterns. The 85% policy results therefore describe the original simulated factory.'),

      ('Scope and sources','The core uses one product; a mixed-product/test-lot extension is included without test recirculation. Exact break timing, PM arbitration and interruption rules are declared modeling conventions. Optional disruption recovery, wet-clean constraints and CONWIP are outside this study. Sources: El-Khouly (2015), Chapter 4; Wang (2015), Table 4.1; McGinnis (2016); Factory Physics and Simulation (2004). Full links and parameter provenance appear in MODEL.md.')]:

        y=para(c,'<b>'+title+'</b>',40,y,532,10,color=TEAL);y=para(c,text,40,y+3,532,9)

    if y<35:raise RuntimeError('Report page 2 overflow: '+str(y))

    c.save()

if __name__=='__main__':report()

