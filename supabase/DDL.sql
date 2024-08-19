CREATE TABLE guessed_languages (
    id SERIAL PRIMARY KEY,
    repo_name VARCHAR,
    hosting_provider VARCHAR,
    file_path VARCHAR,
    guessed_language VARCHAR,
    date_created TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    date_updated TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    hostname VARCHAR
)


-- Create a function to automatically update the `date_updated` column to the
-- current time whenever a row is updated.
CREATE OR REPLACE FUNCTION update_date_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.date_updated = now()
    RETURN NEW
END;
$$ LANGUAGE plpgsql


-- Created a trigger `update_date_updated_trigger` to call the
-- `update_date_updated_column` function before updating any row in the
-- `guessed_languages` table.
CREATE TRIGGER update_date_updated_trigger
BEFORE UPDATE ON guessed_languages
FOR EACH ROW
EXECUTE FUNCTION update_date_updated_column()