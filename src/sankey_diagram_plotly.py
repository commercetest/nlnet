import plotly.graph_objects as go
import pandas as pd
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root
from utils.initial_data_preparation import filter_out_incomplete_urls, get_base_repo_url
import os
from collections import defaultdict

# Setting up the working directory and logger
working_directory = get_working_directory_or_git_root()
logger.info(f"Working directory is: {working_directory}")

# Reading the original data
original_df = pd.read_csv(working_directory / "data/original.csv")
initial_row_count = original_df.shape[0]

# Calculating duplicates and creating a filtered dataframe
num_duplicates = original_df.duplicated().sum()
unique_original_df = original_df.drop_duplicates(keep="first")
after_duplicates_count = unique_original_df.shape[0]

# Simulate filtering out incomplete URLs
# getting the df with complete urls
after_incomplete_urls_df = filter_out_incomplete_urls(unique_original_df)
num_incomplete_urls = unique_original_df.shape[0] - after_incomplete_urls_df.shape[0]
after_incomplete_urls_count = after_duplicates_count - num_incomplete_urls


# Clean and filter URLs
after_incomplete_urls_df["repourl"] = after_incomplete_urls_df["repourl"].apply(
    get_base_repo_url
)

rows_with_nulls = len(after_incomplete_urls_df.isnull().sum())
dropped_null_df = after_incomplete_urls_df.dropna()
rows_after_null_removal = after_incomplete_urls_count - rows_with_nulls

dropped_null_df2 = after_incomplete_urls_df[
    after_incomplete_urls_df["repourl"].notna()
]  # Remove any rows with invalid URLs

cloned_repos_path = working_directory / "data" / "cloned_repos"

# Counting the number of directories in cloned_repos_path
actual_cloned_count = len(
    [
        name
        for name in os.listdir(cloned_repos_path)
        if os.path.isdir(os.path.join(cloned_repos_path, name))
    ]
)

expected_to_clone_count = rows_after_null_removal
successful_clones = actual_cloned_count
failed_clones = expected_to_clone_count - successful_clones

# Nodes for Sankey Diagram
node_labels = [
    "Original Data",
    "After Removing Duplicates",
    "After Removing Incomplete URLs",
    "After Removing Null Values",
    "Expected to Clone",
    "Successfully Cloned",
    "Failed to Clone",
]


# Links for Sankey Diagram
source_indices = [0, 1, 2, 3, 4, 4]
target_indices = [1, 2, 3, 4, 5, 6]

values = [
    after_duplicates_count,
    after_incomplete_urls_count,
    rows_after_null_removal,
    successful_clones,
    failed_clones,
]

# Creating the Sankey Diagram
fig = go.Figure(
    data=[
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=node_labels,
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                # Adding labels for each link indicating the number of excluded rows
                label=[f"{v} rows excluded" for v in values],
            ),
        )
    ]
)

# Adding annotations

# Define vertical spacing
y_step = 0.05  # Value to increase vertical spacing
max_y_position = 0.95  # Starting from the top (near 1), and will decrement
min_y_position = 0.05  # The lowest point for an annotation to be

annotations = []
current_y_position = max_y_position

# Initialise with the initial row count because nothing is excluded at the
# first step
excluded_at_steps = [0]

# Calculate the excluded rows for subsequent steps
for i in range(1, len(values)):
    # The number of excluded rows is the number at the previous step minus the
    # current step
    excluded_at_steps.append(values[i - 1] - values[i])


annotations = []
# Adjust annotations to space out horizontally along the width of the Sankey
# diagram
# # Default horizontal offset for annotations
x_offsets = defaultdict(lambda: 0.05)

for i, (source, target, value) in enumerate(
    zip(source_indices, target_indices, excluded_at_steps)
):
    # If there's a value to annotate, create an annotation dict
    if value > 0:
        # Use the offset for the current source node
        offset = x_offsets[source]
        # Calculate x position as a fraction, adjusted by offset
        x_pos = (
            (source + offset) / (len(node_labels) - 1)
            + (target - offset) / (len(node_labels) - 1)
        ) / 2

        annotations.append(
            dict(
                x=x_pos,  # The x position is normalised between 0 and 1
                y=0.7,  # Keep y in the middle of the plot height
                text=f"{value} rows excluded",  # Annotation text
                showarrow=False,
                font=dict(size=10, color="black"),
                align="center",
                xref="paper",  # Position is relative to the entire plot width
                yref="paper",  # Position is relative to the entire plot height
            )
        )
# Displaying the Sankey Diagram
fig.update_layout(
    title_text="Data Flow: From Original Data to Cloned Repositories",
    font_size=10,
    annotations=annotations,
)

# Saving the diagram
fig.write_html(
    working_directory
    / "reports"
    / "graphs"
    / "sankey-diagram-of-analysis"
    / "sankey-diagram-plotly.html"
)

fig.show()
