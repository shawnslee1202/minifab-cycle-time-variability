"""Verification tests exercise accounting, routing, batches and resource exclusion."""
import unittest
import numpy as np
from model import Config,simulate,PROCESS,LOAD,UNLOAD
class Verification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r,cls.e,cls.l,cls.a,cls.s=simulate(Config(days=30,warm_days=10))
    def test_routing_and_conservation(self):
        for _,g in self.e.groupby('lot_id'):
            self.assertEqual(g.step.tolist(),list(range(1,len(g)+1)))
        self.assertEqual(self.r['ending_wip']+self.l.exit.notna().sum(),len(self.l))
    def test_clock_and_accounting(self):
        e=self.e.dropna(subset=['end'])
        self.assertTrue((e.end>=e.start).all());self.assertTrue((e.start>=e.queue_in).all())
        self.assertAlmostEqual(sum(self.r[f'wip_step_{s}'] for s in range(1,7)),self.r['wip'],places=8)
        for lot,g in e.groupby('lot_id'):
            if len(g)==6:
                self.assertAlmostEqual((g.end-g.queue_in).sum(),self.l.loc[lot,'exit']-self.l.loc[lot,'release'])
    def test_full_batches_compatible(self):
        e=self.e[(self.e.station=='Diffusion')&self.e.start.notna()]
        for _,g in e.groupby('batch_id'):
            self.assertEqual(len(g),3);self.assertEqual(g.step.nunique(),1)
            self.assertTrue((g.operator_id.dropna()==g.unload_operator_id.dropna()).all())
    def test_machine_exclusion(self):
        a=self.a[self.a.kind=='occupied']
        for _,g in a.groupby('machine'):
            g=g.sort_values('start');self.assertTrue(np.all(g.start.to_numpy()[1:]>=g.end.to_numpy()[:-1]-1e-8))
    def test_deterministic_decomposition(self):
        r,e,l,a,s=simulate(Config(D=1,maintenance=False,breaks=False,setup_scale=0,interval=600,days=20,warm_days=0))
        for lot,g in e.dropna(subset=['end']).groupby('lot_id'):
            if len(g)!=6:continue
            service=sum(PROCESS)+sum(LOAD)+sum(UNLOAD)
            queue=(g.start-g.queue_in).sum()
            # Isolated groups can still wait for batch companions and serial service.
            operator_wait=sum((row.process_start-row.start-LOAD[int(row.step)-1])+(row.end-row.process_end-UNLOAD[int(row.step)-1]) for row in g.itertuples())
            self.assertGreaterEqual(operator_wait,-1e-8)
            self.assertAlmostEqual(l.loc[lot,'exit']-l.loc[lot,'release'],service+queue+operator_wait,places=7)
    def test_crn_reproducibility(self):
        x=simulate(Config(days=30,warm_days=10))[0]
        self.assertEqual(x['mean_ct'],self.r['mean_ct'])
    def test_processing_work_conserved(self):
        completed=set(self.e.loc[self.e.end.notna(),'batch_id'])
        aa=self.a[(self.a.kind=='process')&self.a.batch_id.isin(completed)].copy()
        aa['duration']=aa.end-aa.start
        total=aa.groupby('batch_id').duration.sum()
        for batch,minutes in total.items():
            step=int(self.e[self.e.batch_id==batch].step.iloc[0])-1
            self.assertAlmostEqual(minutes,PROCESS[step],places=7)
    def test_pm_has_no_technician_queue_in_duration(self):
        aa=self.a[self.a.kind=='pm']
        for row in aa.itertuples():
            expected=75 if row.machine in ['Ma','Mb'] else (120 if row.machine in ['Mc','Md'] else 30)
            self.assertAlmostEqual(row.end-row.start,expected)
        self.assertGreater(self.r['Me_pm'],0.01)
    def test_partial_batches_and_mix(self):
        r,e,l,a,s=simulate(Config(A=1,mix=True,days=20,warm_days=5))
        for _,g in e[(e.station=='Diffusion')&e.start.notna()].groupby('batch_id'):
            self.assertLessEqual(len(g),3);self.assertEqual(g.step.nunique(),1)
            self.assertLessEqual((g['product']=='TW').sum(),1)
            if g.step.iloc[0]==5:self.assertLessEqual(g.loc[g['product']!='TW','product'].nunique(),1)
if __name__=='__main__':unittest.main(verbosity=2)

