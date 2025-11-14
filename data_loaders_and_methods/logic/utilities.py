from typing import Union

import pandas as pd
from numpy import ndarray
from pandas import Index, Series
from pandas.core.arrays import ExtensionArray
from pandas.core.tools.datetimes import DatetimeScalar

from src.logic.settings import Settings

settings = Settings()

date_time_format = settings.get(key='datetime_format')


def to_pd_datetime(arg: Union[DatetimeScalar, list, tuple, ExtensionArray, ndarray, Index, Series], dt_format=date_time_format, utc=True):
    pd_timestamp = pd.to_datetime(arg=arg, utc=utc, format=dt_format)
    unaware_of_timezone = pd_timestamp.apply(lambda x: x.tz_localize(None))
    return unaware_of_timezone
