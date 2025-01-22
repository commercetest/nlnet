--  Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum type for clone status
CREATE TYPE clone_status AS ENUM ('successful', 'failed', 'pending');

-- Create repositories table
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_ref TEXT,
    nlnet_page TEXT,
    repo_url TEXT NOT NULL,
    repo_domain TEXT,
    base_repo_url TEXT,
    duplicate_flag BOOLEAN DEFAULT false,
    null_value_flag BOOLEAN DEFAULT false,
    unsupported_url_scheme BOOLEAN DEFAULT false,
    incomplete_url_flag BOOLEAN DEFAULT false,
    base_repo_url_flag BOOLEAN DEFAULT false,
    clone_status clone_status DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create basic index
CREATE INDEX idx_repositories_repo_url ON repositories(repo_url);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update the updated_at timestamp
CREATE TRIGGER update_repositories_updated_at
    BEFORE UPDATE ON repositories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();