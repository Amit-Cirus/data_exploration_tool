import os

import pandas as pd

import dcdal

from src.data_loaders.keter_raw_data import get_machine_id_by_name


def load_metadata(machines, stats_pipe_version):
    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    reader = dcdal.DALReader(connection=conn)

    curr_data_object = {}
    for machine_name in machines:
        machine_id = get_machine_id_by_name(machine_name)

        data_sources_df = reader.read_table_to_dataframe(
            schema="preprocessed_raw_data",
            table="data_sources",
            conditions=[f"machine_id = {machine_id}", "has_value = True"],
            columns=['data_source_id', 'short_name',
                     'customer_data_source_id', 'data_source_name'],
        )
        if not data_sources_df.empty:
            data_sources_statistics_df = reader.read_table_to_dataframe(
                schema="statistics_calculation",
                table="data_sources_statistics_mv",
                columns=["data_source_id", "is_periodic",
                         "has_modes_separation",
                         "mode_count", "count_val",
                         "mean_val", "std_val",
                         "cov_val", "entropy",
                         "overall_rank"],
                conditions=[f"run_id = {stats_pipe_version}"],
            )
            merged_data_sources_df = pd.merge(data_sources_df, data_sources_statistics_df,
                                              left_on='data_source_id',
                                              right_on='data_source_id')

            returned_columns = ["data_source_id",
                                'short_name',
                                "overall_rank",
                                "is_periodic",
                                "has_modes_separation",
                                "mode_count",
                                "count_val",
                                "mean_val", "std_val",
                                "cov_val", "entropy", 
                                'customer_data_source_id']
            merged_data_sources_df = merged_data_sources_df[returned_columns]
            merged_data_sources_df = merged_data_sources_df.round(2).sort_values(['cov_val', 'std_val', 'entropy'],
                                                                                 ascending=[False, False, False])

        curr_data_object[machine_id] = data_sources_df if data_sources_df.empty else merged_data_sources_df
        curr_data_object[machine_id] = curr_data_object[machine_id].astype(str)
    return curr_data_object
