import pandas as pd
import subprocess
import os


# Function to count test files
def count_test_files(directory):
    test_file_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if "test" in file.lower() or "test" in root.lower():
                test_file_count += 1
    return test_file_count


# Load the DataFrame
df = pd.read_csv("../data/github_df_test_count.csv")

# Drop the unnamed column
df = df.drop("Unnamed: 0", axis=1)

# Only keep the first row
df_sample = df.head(2)

# Extract the URL from the first row
repo_url = df_sample["repourl"].iloc[1]

# Extract the repo name to use as a local directory name
repo_name = repo_url.split("/")[-1].replace(".git", "")

# Define the desired path relative to the home directory
home_dir = os.path.expanduser("~")
desired_path = os.path.join(home_dir, "data", "cloned_repos", repo_name)

# Ensure the entire desired path exists
os.makedirs(os.path.dirname(desired_path), exist_ok=True)

# Clone the repository into the desired directory
try:
    subprocess.check_call(["git", "clone", repo_url, desired_path])
    print(f"Successfully cloned {repo_name} into {desired_path}")
except subprocess.CalledProcessError as e:
    print(f"Failed to clone {repo_name}. Error: {e}")

# Count the test files in the cloned repository
try:
    test_file_count = count_test_files(desired_path)
    print(f"Test files in {repo_name}: {test_file_count}")
except Exception as e:
    print(f"Error counting test files in {repo_name}. Error: {e}")
