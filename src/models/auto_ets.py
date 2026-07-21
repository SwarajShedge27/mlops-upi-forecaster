# import pandas as pd
# from statsforecast import StatsForecast
# from statsforecast.models import AutoETS, Naive
# from config import FREQ, SEASON_LENGTH, ETS_MODEL

# def fit_auto_ets(df: pd.DataFrame, n_jobs: int = -1) -> StatsForecast:
#     sf = StatsForecast(models=[AutoETS(season_length=SEASON_LENGTH, model=ETS_MODEL)],freq=FREQ,fallback_model=Naive(),n_jobs=n_jobs,)
#     sf.fit(df)
#     return sf

# def predict_auto_ets(sf: StatsForecast, h: int) -> pd.DataFrame:
#     return sf.predict(h=h)

import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoETS, Naive
from config import FREQ, SEASON_LENGTH, ETS_MODEL

def fit_auto_ets_dynamic(df: pd.DataFrame, freq: str = FREQ, season_length: int = SEASON_LENGTH, model_type: str = ETS_MODEL,n_jobs: int = -1) -> StatsForecast:
   
    sf = StatsForecast(models=[AutoETS(season_length=season_length, model=model_type)],freq=freq,fallback_model=Naive(),n_jobs=n_jobs,)
    sf.fit(df)
    return sf
