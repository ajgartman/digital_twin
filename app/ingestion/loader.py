import pandas as pd
from pandas import DataFrame


from app.core.config import Config

# Loader .py file to load the raw .csv

def load_csv(relative_path:str) -> DataFrame | None:
    file_path = Config.DATASET_ROOT / relative_path

    try:
        df = pd.read_csv(file_path)
        return df
    except ValueError:
        print("Invalid CSV file input. Check the contents!")
        return None
