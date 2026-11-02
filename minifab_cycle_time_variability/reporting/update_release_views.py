from pathlib import Path
import json,zipfile,hashlib,sys
import pandas as pd
R=Path(__file__).resolve().parents[2]
D=R/"results"
f=pd.read_csv(D/"final_precision.csv")
precision=f"{int(f.precision_pass.sum())}/96 finite-window cell means have relative 95% interval half-width below 5%. The largest half-width is {100*f.relative_halfwidth.max():.2f}%."
p=R/"dashboard/dist/index.html"
s=p.read_text(encoding="utf-8-sig")
s=s.replace("the published output benchmark is not reproduced, and some cells miss the requested 5% precision.","The external benchmark failed. "+precision+" Factorial charts retain their original paired estimates.")
if "confirmed-estimate" not in s:
    s=s.replace('<div class="controls">','<p id="confirmed-estimate" aria-live="polite"></p><div class="controls">',1)
    j=json.dumps(f.to_dict("records"))
    js="const finalEstimates="+j+";function showFinal(){const r=finalEstimates.find(x=>x.view===$(\x27view\x27).value && x.load===Number($(\x27load\x27).value) && x.scenario===$(\x27scenario\x27).value);if(r)$(\x27confirmed-estimate\x27).textContent=\x27Final cell mean: \x27+r.mean_hours.toFixed(2)+\x27 ± \x27+r.halfwidth.toFixed(2)+\x27 hours (95% CI, n=\x27+r.n+\x27, \x27+r.source+\x27).\x27;}[\x27view\x27,\x27load\x27,\x27scenario\x27].forEach(k=>$(k).addEventListener(\x27change\x27,showFinal));showFinal();"
    s=s.replace("</script></body>",js+"</script></body>")
p.write_text(s,encoding="utf8")
