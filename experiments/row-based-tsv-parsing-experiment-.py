"""Second attempt to correctly process single column rows.

I'd tried using
    y = df.iloc[:,-1:]
to only obtain the last column in the dataframe in tsv_parsing_experiment.py
but that didn't work. This code is the result.
"""

import pandas as pd

# Define the path to your TSV file
file_path = "project_repos_from_jos_2024-feb-22.tsv"

# First, read the data line by line. Store records with only 1 column in the 3rd column;
# Store records with 3 columns directly.
df = pd.DataFrame()
with open(file_path, "r") as f:
    for line in f:
        parsed_line = line.strip().split("\t")
        if len(parsed_line) == 1:
            data = [(pd.NA, pd.NA, parsed_line[0])]
            temp_df = pd.DataFrame.from_records(data)
            df = pd.concat([df, temp_df], ignore_index=True)
        elif len(parsed_line) == 3:
            df = pd.concat([df, pd.DataFrame([tuple(parsed_line)])], ignore_index=True)
        else:
            raise ValueError("Unexpected number of columns in the file.")

# Add column names, these will do for now
df.columns = ["projectref", "nlnetpage", "repourl"]

# For projects with several code repos, copy the project ref and NLnet page info
# from the previous record which has these details.
df["projectref"] = df["projectref"].ffill()
df["nlnetpage"] = df["nlnetpage"].ffill()

# Print a subset of the resulting rows to visually confirm the expected info is present.
print(df.iloc[0:31:1])
