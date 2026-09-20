from app.ingestion.loader import load_csv
from app.ingestion.validation import validate_dataframe
from app.ingestion.metadata_parser import parser

# TESTING ENVIRONMENT!
test_path = "Electric/Motor-2/50/healthy 1/Electric_Motor-2_50_time-healthy 1-ch1.csv"

# metadata parsing
print("--- Metadata Parsing ---")
metadata = parser(test_path)
print(metadata)

def test(path):
    df = load_csv(path)
    return df

result = test(test_path)
# Testing edge cases
# Warning
warning_df = result.iloc[:299000]
# Error
bad_df = result.iloc[:280000]
# Missing values
nan_df = result.copy()
nan_df.iloc[100, 1] = None
# Combination
test_df = result.iloc[:299000].copy()
test_df.iloc[100, 1] = None

# validation
print("--- Dataset validation! ---")
print(validate_dataframe(test_df,metadata))