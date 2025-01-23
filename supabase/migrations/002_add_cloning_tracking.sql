-- Create enum for clone status
CREATE TYPE clone_status AS ENUM ('pending', 'successful', 'failed');

-- Create repository cloning operations table
CREATE TABLE repository_cloning (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    clone_status clone_status DEFAULT 'pending',
    cloned_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for cloned files
CREATE TABLE cloned_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_extension TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_repo_cloning_repository_id ON repository_cloning(repository_id);
CREATE INDEX idx_repo_cloning_status ON repository_cloning(clone_status);
CREATE INDEX idx_cloned_files_repository_id ON cloned_files(repository_id);
CREATE INDEX idx_cloned_files_extension ON cloned_files(file_extension);

-- -- Enable RLS
-- ALTER TABLE repository_cloning ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cloned_files ENABLE ROW LEVEL SECURITY;
--
-- -- Create policies
-- CREATE POLICY "Allow full access to authenticated users" ON repository_cloning
--     FOR ALL TO authenticated USING (true) WITH CHECK (true);
--
-- CREATE POLICY "Allow full access to authenticated users" ON cloned_files
--     FOR ALL TO authenticated USING (true) WITH CHECK (true);