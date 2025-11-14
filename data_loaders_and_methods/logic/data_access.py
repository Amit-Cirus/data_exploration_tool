import os
from typing import List, Optional

from loguru import logger as log

import dcdal
from pandas import DataFrame

from src.logic.exceptions import AppException


def df_from_db(schema: str, table: str, columns: List[str], conditions: Optional[List] = None) -> DataFrame:
    try:
        conn = dcdal.DALConnection(
            host=os.environ["DB_HOST"],
            db=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )
        reader = dcdal.DALReader(connection=conn)
        df = reader.read_table_to_dataframe(
            schema=schema,
            table=table,
            columns=columns,
            conditions=conditions
        )
        conn.close()
        return df
    except Exception as e:
        error_message = f'Failed fetching from {schema}.{table} columns [{columns}] due to: {e}'
        log.error(error_message)
        raise AppException(error_message)
