"""Package SQL-derived views and the balanced experiment's curves for Tableau."""
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import pandas as pd
R=Path(__file__).resolve().parent
OUT=R/"tableau"
def add(parent,tag,**attributes):
    return ET.SubElement(parent,tag,{k:str(v) for k,v in attributes.items()})

def main():
    OUT.mkdir(exist_ok=True)
    data=OUT/"Data"
    data.mkdir(exist_ok=True)
    r=pd.read_csv(R/"results/runs.csv")
    group=r.query("view=='equal_starts' and load==.85 and scenario=='Baseline'")
    wip=group.filter(regex=r"^wip_step_").mean()
    with sqlite3.connect(R/"results/reporting.sqlite") as db:
        moves=pd.read_sql_query("SELECT day, SUM(moves) AS moves, MAX(target_moves)*6 AS target FROM moves_per_day WHERE run_id='equal_starts_85_Baseline_0' GROUP BY day ORDER BY day DESC LIMIT 28",db)
        lots=pd.read_sql_query("SELECT CAST(cycle_time_hours/4 AS INTEGER)*4 AS bin_start,COUNT(*) AS lots FROM cycle_time_per_lot WHERE run_id='equal_starts_85_Baseline_0' AND measurement_departure=1 GROUP BY 1 ORDER BY 1",db)
    moves=moves.melt(id_vars="day",var_name="series",value_name="moves_per_day")
    curves=pd.read_csv(R/"results/summary.csv").query("view=='equal_starts' and scenario in ['Baseline','A','B','C','D','ABCD']")[["scenario","throughput","mean_hours"]]
    sheets=[
        ("Operating curves - equal starts",curves,"throughput","mean_hours","scenario","Line"),
        ("WIP by step - 85 percent baseline",pd.DataFrame({"step":["Step "+str(i) for i in range(1,7)],"lots":wip.values}),"step","lots",None,"Bar"),
        ("Moves and target - final 28 days",moves,"day","moves_per_day","series","Line"),
        ("Baseline CT - four-hour bins",lots,"bin_start","lots",None,"Bar")]
    book=ET.Element("workbook",{"version":"18.1","source-platform":"win"})
    sources=add(book,"datasources")
    worksheets=add(book,"worksheets")
    for i,(title,frame,x,y,color,mark) in enumerate(sheets):
        key=f"view{i+1}"
        filename=key+".csv"
        frame.to_csv(data/filename,index=False)
        dsname="textscan."+key
        ds=add(sources,"datasource",caption=title,inline="true",name=dsname,version="18.1")
        conn=add(ds,"connection",**{"class":"federated"})
        nc=add(add(conn,"named-connections"),"named-connection",caption=key,name=key)
        add(nc,"connection",**{"class":"textscan","directory":"Data","filename":filename})
        relation=add(conn,"relation",connection=key,name=key,table=f"[{key}#csv]",type="table")
        columns=add(relation,"columns",**{"character-set":"UTF-8","header":"yes","locale":"en_US","separator":","})
        table=add(add(worksheets,"worksheet",name=title),"table")
        view=add(table,"view")
        add(add(view,"datasources"),"datasource",caption=title,name=dsname)
        dep=add(view,"datasource-dependencies",datasource=dsname)
        fields={}
        for j,k in enumerate(frame):
            dimension=(k==x or k==color)
            numeric=pd.api.types.is_numeric_dtype(frame[k])
            datatype="real" if numeric else "string"
            typ="quantitative" if numeric else "nominal"
            add(columns,"column",datatype=datatype,name=k,ordinal=j)
            attrs=dict(datatype=datatype,name=f"[{k}]",role="dimension" if dimension else "measure",type=typ)
            add(ds,"column",**attrs)
            add(dep,"column",**attrs)
            agg="None" if dimension else "Avg"
            name=f"[{agg.lower()}:{k}:{'qk' if numeric else 'nk'}]"
            fields[k]=f"[{dsname}].{name}"
            add(dep,"column-instance",column=f"[{k}]",derivation=agg,name=name,pivot="key",type=typ)
        add(view,"aggregation",value="true")
        add(table,"style")
        pane=add(add(table,"panes"),"pane")
        add(add(pane,"view"),"breakdown",value="auto")
        add(pane,"mark",**{"class":mark})
        if color: add(add(pane,"encodings"),"color",column=fields[color])
        add(table,"rows").text=fields[y]
        add(table,"cols").text=fields[x]
    dash=add(add(book,"dashboards"),"dashboard",name="Mini-Fab operations")
    add(dash,"style")
    add(dash,"size",maxheight=800,maxwidth=1200,minheight=800,minwidth=1200,**{"sizing-mode":"fixed"})
    zones=add(dash,"zones")
    banner=add(zones,"zone",type="text",id=5,h=12000,w=100000,x=0,y=0)
    add(add(banner,"formatted-text"),"run",bold="true",fontsize=15).text="Mini-Fab operations | Balanced experiment. 85% baseline detail uses replication 0 for moves and CT. Published benchmark failed."
    for i,(name,*_) in enumerate(sheets):
        add(zones,"zone",id=i+1,name=name,x=(i%2)*50000,y=12000+(i//2)*44000,w=50000,h=44000)
    path=OUT/"Mini-Fab.twb"
    ET.indent(book)
    ET.ElementTree(book).write(path,encoding="utf-8",xml_declaration=True)
    with ZipFile(OUT/"Mini-Fab.twbx","w",ZIP_DEFLATED) as z:
        z.write(path,path.name)
        for csv in sorted(data.glob("*.csv")):z.write(csv,"Data/"+csv.name)
    with ZipFile(OUT/"Mini-Fab.twbx") as z:
        assert z.testzip() is None and len(ET.fromstring(z.read(path.name)).findall(".//worksheet"))==4

if __name__=="__main__":
    main()
