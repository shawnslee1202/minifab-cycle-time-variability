"""Mini-Fab DES. Minutes and lots; source/convention register in MODEL.md."""
from dataclasses import dataclass, asdict
import random
import numpy as np
import pandas as pd
import simpy
PROCESS=[225,30,55,50,255,10]
LOAD=[20,15,10,15,20,10]
UNLOAD=[40,15,10,15,40,10]
STATION=[0,1,2,1,0,2]
NAMES=['Diffusion','Implant','Lithography']
@dataclass
class Config:
    load:float=.85
    A:int=0
    B:int=0
    C:int=0
    D:int=0
    rep:int=0
    warm_days:float=90
    days:float=365
    interval:float=0
    partial_wait:float=120
    setup_scale:float=-1
    repair_scale:float=-1
    mix:bool=False
    maintenance:bool=True
    breaks:bool=True
    thesis_reference:bool=False
    personnel_constraints:bool=True
    view:str='equal_starts'
    seed:int=20261027
    @property
    def scenario(self):return ''.join(k for k in 'ABCD' if getattr(self,k)) or 'Baseline'
    @property
    def mean_interval(self):return self.interval or 115/((690/720)*self.load)
class Fab:
    process_minutes = PROCESS
    unload_minutes = UNLOAD

    def setup_minutes(self, previous, step, product):
        if previous is None:
            return 0.0
        old_step, old_product = previous
        if old_step != step and old_product != product:
            return 12.0
        if old_step != step:
            return 10.0
        return 5.0 if old_product != product else 0.0

    def __init__(self,cfg):
        self.cfg=cfg; self.env=simpy.Environment()
        self.q=[[] for _ in range(3)];self.signal=[self.env.event() for _ in range(3)]
        self.ops=simpy.FilterStore(self.env,2 if cfg.personnel_constraints else 10);self.ops.items=['PO1','PO2'] if cfg.personnel_constraints else ['PO1']*5+['PO2']*5
        self.tech=simpy.PriorityResource(self.env,1 if cfg.personnel_constraints else 100)
        seed=cfg.seed+cfg.rep*10007
        self.arr_rng=random.Random(seed+1);self.mix_rng=random.Random(seed+2)
        self.events=[];self.lots=[];self.activity=[];self.samples=[];self.batch=0
        self.stop=(cfg.warm_days+cfg.days)*1440;self.warm=cfg.warm_days*1440
        self.machines=[];self.active_wip=0;self.maintenance_signal=self.env.event()
        for i,s in enumerate([0,0,1,1,2]):
            m=dict(name='M'+chr(97+i),station=s,gate=simpy.Resource(self.env,1),down=False,
                change=self.env.event(),previous=None,rng=random.Random(seed+10+i),repair_rng=random.Random(seed+20+i))
            self.machines.append(m);self.env.process(self.worker(m))
            if cfg.maintenance:
                self.env.process(self.pm(m,i))
                if s==1:self.env.process(self.failure(m))
        if cfg.breaks and cfg.personnel_constraints:
            for op,offset in [('PO1',0),('PO2',60)]:self.env.process(self.operator_break(op,offset))
            self.env.process(self.tech_break())
        self.env.process(self.release());self.env.process(self.sample())
    def wake(self,s):
        old=self.signal[s];self.signal[s]=self.env.event();old.succeed()
    def arrive(self,lot,step):
        r=dict(lot_id=lot['lot_id'],product=lot['product'],step=step+1,station=NAMES[STATION[step]],
            machine=None,batch_id=None,queue_in=self.env.now,start=None,end=None,operator_id=None,
            unload_operator_id=None,process_start=None,process_end=None,setup_minutes=0.,
            scenario=self.cfg.scenario,replication=self.cfg.rep)
        self.events.append(r);self.q[STATION[step]].append((lot,step,r));self.wake(STATION[step])
    def release(self):
        while True:
            gap=self.cfg.mean_interval if self.cfg.D else self.arr_rng.expovariate(1/self.cfg.mean_interval)
            yield self.env.timeout(gap)
            p=self.mix_rng.choices(['Pa','Pb','TW'],([61,36,3] if self.cfg.thesis_reference else [51,30,3]))[0] if self.cfg.mix else 'Pa'
            lot=dict(lot_id=len(self.lots),product=p,release=self.env.now,exit=None)
            self.lots.append(lot);self.active_wip+=1;self.arrive(lot,0)
    def eligible(self,q):
        candidates=[]
        for first in q:
            group=[first]
            for x in q:
                if x is first or x[1]!=first[1]:continue
                if not self.cfg.thesis_reference and x[0]['product']=='TW' and any(y[0]['product']=='TW' for y in group):continue
                prod={y[0]['product'] for y in group if y[0]['product']!='TW'}
                if not self.cfg.thesis_reference and x[1]==4 and prod and x[0]['product'] not in prod|{'TW'}:continue
                group.append(x)
                if len(group)==3:return group,0
            if self.cfg.A:
                remaining=self.cfg.partial_wait-(self.env.now-max(x[2]['queue_in'] for x in group))
                if remaining<=1e-8:return group,0
                candidates.append(remaining)
        return None,min(candidates) if candidates else None
    def wait_up(self,m):
        while m['down']:yield m['change']
    def work(self,m,duration,kind,batch):
        left=duration
        while left>1e-8:
            yield from self.wait_up(m)
            start=self.env.now
            yield self.env.timeout(left)|m['change']
            elapsed=self.env.now-start
            if elapsed:self.activity.append((m['name'],kind,start,self.env.now,batch))
            left-=elapsed
    def worker(self,m):
        s=m['station']
        while True:
            q=self.q[s]
            group,delay=self.eligible(q) if s==0 else ((q[:1],0) if q else (None,None))
            if not group:
                signal=self.signal[s]
                if delay is None:yield signal
                else:yield signal|self.env.timeout(delay)
                continue
            with m['gate'].request() as req:
                yield req;yield from self.wait_up(m)
                q=self.q[s];group,_=self.eligible(q) if s==0 else ((q[:1],0) if q else (None,None))
                if not group:continue
                for x in group:q.remove(x)
                self.batch+=1;batch=self.batch;step=group[0][1];lot=group[0][0];start=self.env.now
                for _,_,r in group:r.update(start=start,machine=m['name'],batch_id=batch)
                setup=0
                if s==2 and m['previous'] is not None:
                    setup=self.setup_minutes(m['previous'],step,lot['product'])
                    setup*=self.cfg.setup_scale if self.cfg.setup_scale>=0 else (.5 if self.cfg.B else 1.)
                if setup:yield from self.work(m,setup,'setup',batch)
                m['previous']=(step,lot['product'])
                allowed=['PO1'] if s==0 else (['PO2'] if s==2 else ['PO1','PO2'])
                yield from self.wait_up(m)
                op=yield self.ops.get(lambda x:x in allowed)
                while m['down']:
                    yield self.ops.put(op);yield from self.wait_up(m)
                    op=yield self.ops.get(lambda x:x in allowed)
                ls=self.env.now
                yield self.env.timeout(LOAD[step]);self.activity.append((m['name'],'load',ls,self.env.now,batch))
                yield self.ops.put(op);yield from self.wait_up(m);ps=self.env.now
                yield from self.work(m,self.process_minutes[step],'process',batch);pe=self.env.now
                yield from self.wait_up(m)
                uop=yield self.ops.get(lambda x:x==op if s==0 else x in allowed)
                while m['down']:
                    yield self.ops.put(uop);yield from self.wait_up(m)
                    uop=yield self.ops.get(lambda x:x==op if s==0 else x in allowed)
                us=self.env.now
                yield self.env.timeout(self.unload_minutes[step]);self.activity.append((m['name'],'unload',us,self.env.now,batch))
                yield self.ops.put(uop);end=self.env.now
                self.activity.append((m['name'],'occupied',start,end,batch))
                for l,st,r in group:
                    r.update(end=end,operator_id=op,unload_operator_id=uop,process_start=ps,process_end=pe,setup_minutes=setup)
                    if st==5:l['exit']=end;self.active_wip-=1
                    else:self.arrive(l,st+1)
            self.notify_maintenance()
            yield self.env.timeout(0)
    def notify_maintenance(self):
        old=self.maintenance_signal;self.maintenance_signal=self.env.event();old.succeed()
    def pm(self,m,index):
        period=[1440,720,720][m['station']];duration=[75,120,30][m['station']]
        due=period+(index%2)*period/2
        while True:
            yield self.env.timeout(max(0,due-self.env.now))
            # Atomic acquisition: tool continues production until technician AND tool free.
            while m['gate'].count or self.tech.count>=self.tech.capacity or m['down']:
                yield self.maintenance_signal
            with self.tech.request(priority=1) as tr, m['gate'].request() as mr:
                yield tr & mr
                start=self.env.now
                yield self.env.timeout(duration)
                self.activity.append((m['name'],'pm',start,self.env.now,None))
            self.notify_maintenance()
            due+=period
            if due<self.env.now:due=self.env.now+period
    def failure(self,m):
        while True:
            yield self.env.timeout(m['rng'].uniform(1440,4560));start=self.env.now
            m['down']=True;old=m['change'];m['change']=self.env.event();old.succeed()
            scale=self.cfg.repair_scale if self.cfg.repair_scale>=0 else (.5 if self.cfg.C else 1)
            with self.tech.request(priority=0) as req:
                yield req;yield self.env.timeout(m['repair_rng'].uniform(360,480)*scale)
            self.activity.append((m['name'],'repair',start,self.env.now,None))
            m['down']=False;old=m['change'];m['change']=self.env.event();old.succeed();self.notify_maintenance()
    def operator_break(self,op,offset):
        shift=0
        while True:
            for t in [180,360,540]:
                yield self.env.timeout(max(0,shift+t+offset-self.env.now))
                token=yield self.ops.get(lambda x:x==op);yield self.env.timeout(60);yield self.ops.put(token)
            shift+=720
    def tech_break(self):
        shift=0
        while True:
            for t,d in [(150,45),(345,45),(570,30)]:
                yield self.env.timeout(max(0,shift+t-self.env.now))
                with self.tech.request(priority=2) as req:
                    yield req;yield self.env.timeout(d)
                self.notify_maintenance()
            shift+=720
    def sample(self):
        while True:
            self.samples.append((self.env.now,self.active_wip))
            yield self.env.timeout(1440)
    def run(self):
        self.env.run(until=self.stop)
        e=pd.DataFrame(self.events);l=pd.DataFrame(self.lots)
        a=pd.DataFrame(self.activity,columns=['machine','kind','start','end','batch_id'])
        done=l[(l.exit>=self.warm)&(l.exit<self.stop)];ct=(done.exit-done.release).to_numpy()
        window=self.stop-self.warm
        area=np.maximum(0,np.minimum(l.exit.fillna(self.stop),self.stop)-np.maximum(l.release,self.warm)).sum()
        wip=area/window;th=len(done)/window
        r=asdict(self.cfg)|dict(scenario=self.cfg.scenario,interval_actual=self.cfg.mean_interval,
            mean_ct=ct.mean(),sd_ct=ct.std(ddof=1),p95_ct=np.quantile(ct,.95),x_factor=ct.mean()/sum(PROCESS),
            wip=wip,throughput_day=th*1440,completed=len(done),
            released=int(((l.release>=self.warm)&(l.release<self.stop)).sum()),
            little_relative_error=(wip-th*ct.mean())/wip,ending_wip=int(l.exit.isna().sum()))
        starts=e[(e.start>=self.warm)&(e.start<self.stop)];diff=starts[starts.station=='Diffusion']
        r['batch_fill']=len(diff)/(3*diff.batch_id.nunique())
        r['setups_day']=len(a[(a.kind=='setup')&(a.start>=self.warm)])/self.cfg.days
        for machine in ['Ma','Mb','Mc','Md','Me']:
            aa=a[a.machine==machine]
            clipped=np.maximum(0,np.minimum(aa.end,self.stop)-np.maximum(aa.start,self.warm))
            for kind in ['process','load','unload','setup','occupied','pm','repair']:
                r[machine+'_'+kind]=float(clipped[aa.kind==kind].sum()/window)
        r['litho_util']=r['Me_occupied']/max(.001,1-r['Me_pm'])
        r['litho_analytic_util']=th*(105+r['Me_setup']*window/max(1,len(done)))/(1-r['Me_pm'])
        for step in range(1,7):
            ss=e[e.step==step]
            exposure=np.maximum(0,np.minimum(ss.end.fillna(self.stop),self.stop)-np.maximum(ss.queue_in,self.warm))
            r[f'wip_step_{step}']=exposure.sum()/window
        return r,e,l,a,pd.DataFrame(self.samples,columns=['time','wip'])
def simulate(cfg):return Fab(cfg).run()




