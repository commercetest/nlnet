ALTER TABLE cloned_files
ADD COLUMN IF NOT EXISTS lines_of_code INTEGER,
ADD COLUMN IF NOT EXISTS number_of_functions INTEGER,
ADD COLUMN IF NOT EXISTS number_of_test_cases INTEGER,
ADD COLUMN IF NOT EXISTS number_of_assertions INTEGER,
ADD COLUMN IF NOT EXISTS has_setup_teardown BOOLEAN,
ADD COLUMN IF NOT EXISTS complexity_score INTEGER,
ADD COLUMN IF NOT EXISTS cyclomatic_complexity INTEGER,
ADD COLUMN IF NOT EXISTS metrics_processed_at TIMESTAMP;
    