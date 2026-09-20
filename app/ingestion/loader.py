import pandas as pd
from app.core.config import Config

# Loader .py file to load the raw .csv

def load_csv(relative_path:str) -> pd.DataFrame:
    file_path = Config.DATASET_ROOT / relative_path
    return pd.read_csv(file_path)
