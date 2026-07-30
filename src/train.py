# import pandas as pd
# from statsforecast import StatsForecast
# from models.auto_ets import fit_auto_ets_dynamic
# from models.baseline import fit_naive_baseline_dynamic
# from config import FREQ, SEASON_LENGTH

# def train_models_in_memory(train_df: pd.DataFrame, freq: str = FREQ, season_length: int = SEASON_LENGTH) -> tuple[StatsForecast, StatsForecast]:
   
#     sf_ets = fit_auto_ets_dynamic(train_df, freq=freq, season_length=season_length)

#     sf_baseline = fit_naive_baseline_dynamic(train_df, freq=freq)

#     return sf_ets, sf_baseline


import pandas as pd
from statsforecast import StatsForecast
from models.auto_ets import fit_auto_ets_dynamic
from models.baseline import fit_naive_baseline_dynamic
from config import FREQ, SEASON_LENGTH, ETS_MODEL

def train_models_in_memory(train_df: pd.DataFrame, freq: str = FREQ, season_length: int = SEASON_LENGTH,model_type: str = ETS_MODEL) -> tuple[StatsForecast, StatsForecast]:
   
    # Forward the model_type choice to AutoETS fit
    sf_ets = fit_auto_ets_dynamic(train_df, freq=freq, season_length=season_length, model_type=model_type)

    sf_baseline = fit_naive_baseline_dynamic(train_df, freq=freq)

    return sf_ets, sf_baseline
