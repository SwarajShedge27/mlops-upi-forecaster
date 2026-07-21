# import pandas as pd
# from statsforecast import StatsForecast
# from statsforecast.models import Naive
# from config import FREQ

# def fit_naive_baseline(df: pd.DataFrame) -> StatsForecast:
#     sf = StatsForecast(models=[Naive()], freq=FREQ)
#     sf.fit(df)
#     return sf

import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import Naive
from config import FREQ

def fit_naive_baseline_dynamic(df: pd.DataFrame, freq: str = FREQ) -> StatsForecast:
    sf = StatsForecast(models=[Naive()], freq=freq)
    sf.fit(df)
    return sf
