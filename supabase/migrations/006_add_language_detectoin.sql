-- Add column for extension_based language detection
ALTER table cloned_files
ADD COLUMN IF NOT EXISTS file_language text,
ADD COLUMN IF NOT EXIST language_detection_processed_at timestamp with time
    zone;

-- Add comments to explain columns
COMMENT ON COLUMN cloned_files.file_language IS 'Programming language ' ||
        'determined based on file extension'
COMMENT ON COLUMN cloned_files.language_detection_processed_at IS 'Timestamp ' ||
        'when language detection was performed (based on file extension)'