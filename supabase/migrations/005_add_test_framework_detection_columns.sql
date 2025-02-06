-- Add main test framework columns
ALTER TABLE cloned_files
ADD COLUMN has_test_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN detected_test_framework TEXT[];

-- High Priority Frameworks (>10K files)
ALTER TABLE cloned_files
ADD COLUMN phpunit_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN go_test_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN jest_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN mocha_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN pytest_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN unittest_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN junit_framework BOOLEAN DEFAULT FALSE,

-- Second Priority Frameworks (>5K files)
ADD COLUMN gtest_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN catch2_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN rust_test_framework BOOLEAN DEFAULT FALSE,
ADD COLUMN kotlin_test_framework BOOLEAN DEFAULT FALSE,

-- Detection method columns
ADD COLUMN framework_detected_by_dependency BOOLEAN DEFAULT FALSE,
ADD COLUMN framework_detected_by_config BOOLEAN DEFAULT FALSE,
ADD COLUMN framework_detected_by_pattern BOOLEAN DEFAULT FALSE,
ADD COLUMN framework_detected_by_content BOOLEAN DEFAULT FALSE,

-- Processing status
ADD COLUMN framework_detection_processed_at TIMESTAMP WITH TIME ZONE;

-- Create indexes
CREATE INDEX idx_cloned_files_test_framework ON cloned_files(has_test_framework);
CREATE INDEX idx_cloned_files_framework_processed ON cloned_files(framework_detection_processed_at);