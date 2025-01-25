ALTER TABLE cloned_files
ADD COLUMN has_test_in_name_or_path BOOLEAN DEFAULT FALSE,
ADD COLUMN processed_at TIMESTAMP WITH TIME ZONE;


CREATE INDEX idx_cloned_files_processed ON cloned_files(processed_at);





-- ADD COLUMN has_test_framework BOOLEAN DEFAULT FALSE,
-- ADD COLUMN test_framework TEXT,
-- ADD COLUMN last_commit_hash TEXT;
-- ADD COLUMN processed_at  WITH TIME ZONE,
--
-- -- Add test framework detection method columns for each framework
-- ADD COLUMN junit_dependency BOOLEAN DEFAULT FALSE,
-- ADD COLUMN junit_config BOOLEAN DEFAULT FALSE,
-- ADD COLUMN junit_pattern BOOLEAN DEFAULT FALSE,
-- ADD COLUMN junit_content BOOLEAN DEFAULT FALSE,
-- ADD COLUMN pytest_dependency BOOLEAN DEFAULT FALSE,
-- ADD COLUMN pytest_config BOOLEAN DEFAULT FALSE,
-- ADD COLUMN pytest_pattern BOOLEAN DEFAULT FALSE,
-- ADD COLUMN pytest_content BOOLEAN DEFAULT FALSE,
-- ADD COLUMN mocha_dependency BOOLEAN DEFAULT FALSE,
-- ADD COLUMN mocha_config BOOLEAN DEFAULT FALSE,
-- ADD COLUMN mocha_pattern BOOLEAN DEFAULT FALSE,
-- ADD COLUMN mocha_content BOOLEAN DEFAULT FALSE;
--
-- -- Create indexes
-- CREATE INDEX idx_cloned_files_test_name ON cloned_files(has_test_in_name);
-- CREATE INDEX idx_cloned_files_test_framework ON cloned_files(test_framework);
-- CREATE INDEX idx_cloned_files_framework ON cloned_files(has_test_framework);
-- CREATE INDEX idx_cloned_files_processed ON cloned_files(processed_at);