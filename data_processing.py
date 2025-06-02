import pandas as pd
import re

# Show full content in each column (no truncation)
pd.set_option('display.max_colwidth', None)

# Load the data
df = pd.read_csv("amazon_data.csv")

# Replace line breaks in prices
df["price"] = df["price"].str.replace("\n", ".", regex=False)

# Merge title and resume, drop resume
df.rename(columns={"name": "title"}, inplace=True)
df["title"] = df["title"] + " " + df["resume"].fillna("")
df.drop(columns=["resume"], inplace=True)

# Extract numeric rating or return "N/A" if invalid
def extract_rating(rating_str):
    if str(rating_str).strip() in ["", "N/A"]:
        return "N/A"
    match = re.search(r"(\d+(\.\d+)?)", str(rating_str))
    return match.group(1) if match else "N/A"

df["rating"] = df["rating"].apply(extract_rating)

# replace "N/A" with the "" for every column
def replace_na_with_empty(df):
    for col in df.columns:
        df[col] = df[col].replace("N/A", "")
    return df

df = replace_na_with_empty(df)


# Save to CSV
df.to_csv("amazon_scraping_data_pfa.csv", index=False, encoding='utf-8')
