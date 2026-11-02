-- SQLite reporting views. Run with build_reporting.py.
-- Events contain warm-up, measurement, and unfinished visits; use run window explicitly.
CREATE VIEW IF NOT EXISTS cycle_time_per_lot AS
SELECT l.run_id,l.lot_id,l.product,l.release,l.exit,(l.exit-l.release)/60.0 AS cycle_time_hours,
       CASE WHEN l.exit>=r.warm_days*1440 AND l.exit<(r.warm_days+r.days)*1440 THEN 1 ELSE 0 END AS measurement_departure
FROM lots l JOIN runs r USING(run_id) WHERE l.exit IS NOT NULL;
CREATE VIEW IF NOT EXISTS moves_per_day AS
SELECT e.run_id,CAST(e.end/1440 AS INTEGER) AS day,e.step,COUNT(*) AS moves,
       1440.0/r.interval_actual AS target_moves
FROM events e JOIN runs r USING(run_id)
WHERE e.end>=r.warm_days*1440 AND e.end<(r.warm_days+r.days)*1440
GROUP BY e.run_id,day,e.step;
CREATE VIEW IF NOT EXISTS wip_step_deltas AS
SELECT run_id,queue_in AS time,step,1 AS delta FROM events
UNION ALL SELECT run_id,end AS time,step,-1 AS delta FROM events WHERE end IS NOT NULL;
CREATE VIEW IF NOT EXISTS wip_by_step_over_time AS
SELECT run_id,time,step,SUM(SUM(delta)) OVER(PARTITION BY run_id,step ORDER BY time ROWS UNBOUNDED PRECEDING) AS wip
FROM wip_step_deltas GROUP BY run_id,time,step;
-- Machine activity is recorded once per run, not once per lot in a batch.
CREATE VIEW IF NOT EXISTS utilization_by_machine AS
SELECT a.run_id,a.machine,a.kind,
SUM(MAX(0,MIN(a.end,(r.warm_days+r.days)*1440)-MAX(a.start,r.warm_days*1440)))/(r.days*1440) AS fraction
FROM activity a JOIN runs r USING(run_id) GROUP BY a.run_id,a.machine,a.kind;
-- Split intervals across midnight; never assign an entire multi-day repair to its start day.
CREATE VIEW IF NOT EXISTS setups_and_downtime_by_day AS
WITH RECURSIVE slices(run_id,machine,kind,start,end,day,lastday) AS (
 SELECT run_id,machine,kind,start,end,CAST(start/1440 AS INTEGER),CAST((end-0.0000001)/1440 AS INTEGER)
 FROM activity WHERE kind IN ('setup','repair','pm')
 UNION ALL SELECT run_id,machine,kind,start,end,day+1,lastday FROM slices WHERE day<lastday
)
SELECT run_id,machine,kind,day,SUM(MIN(end,(day+1)*1440)-MAX(start,day*1440)) AS minutes,
SUM(CASE WHEN CAST(start/1440 AS INTEGER)=day THEN 1 ELSE 0 END) AS starts
FROM slices GROUP BY run_id,machine,kind,day;
