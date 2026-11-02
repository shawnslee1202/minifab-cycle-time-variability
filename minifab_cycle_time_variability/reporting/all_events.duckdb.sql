-- Start duckdb from the project root after converting any legacy gzip files.
CREATE OR REPLACE VIEW events_all AS SELECT * FROM read_parquet('results/events/*.parquet',union_by_name=true) WHERE step IS NOT NULL;
-- Prefer the file manifest in results/event_manifest.csv to distinguish visit, lot, activity and WIP tables.
