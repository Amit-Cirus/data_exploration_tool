import os
from typing import List, Dict

import pandas as pd
import psycopg

import dcdal

from src.keter_globals import *
from src.logic.data_access import df_from_db


# TODO: Concat with function get_machines_metadata_df (this function is just the subversion of it)
def get_machines():
    machines_df = df_from_db(
        schema='preprocessed_raw_data',
        table='machines',
        columns=["machine_id", "customer_machine_id"])

    machine_id_to_customer_id = {
        machine["machine_id"]: machine["customer_machine_id"]
        for _, machine in machines_df.iterrows()
    }
    return machine_id_to_customer_id


def get_machine_names(machine_object):
    return [f"{key}-{value}" for key, value in machine_object.items()]


def get_machine_id_by_name(machine_name):
    return machine_name.split("-")[0]


def get_data_sources_by_machine(machine_id):
    data_sources_df = df_from_db(
        schema="preprocessed_raw_data",
        table="data_sources",
        conditions=[f"machine_id = {machine_id}", "has_value = True"],
        columns=['data_source_id', 'short_name', 'customer_data_source_id', 'data_source_name']
    )

    if data_sources_df.empty:
        return {}
    return {
        node["data_source_id"]: node["customer_data_source_id"]
        if (node["short_name"] == '') or node["short_name"] == 'None' else node["short_name"]
        for i, node in data_sources_df.iterrows()
    }


def get_data_sources_names(data_sources_object, filter_list=None):
    if filter_list is None:
        return [f"{key}-{value}" for key, value in data_sources_object.items()]
    else:
        return [f"{key}-{data_sources_object[int(key)]}" for key in filter_list]


def get_data_source_id_by_name(data_source_name):
    return int(data_source_name.split("-")[0])


def get_machines_metadata_from_db():
    machines_df = df_from_db(
        schema="preprocessed_raw_data",
        table="machines",
        columns=[
            "machine_id",
            "machine_name",
            "machine_type",
            "description",
            "local_timezone",
            "customer_machine_id"]
    )

    return machines_df


def get_machines_metadata_from_csv():
    return pd.DataFrame()


def load_data(
        data_source_id_list: List[int],
        start_time: datetime = None,
        end_time: datetime = None,
) -> Dict[int, Dict[int, pd.DataFrame]]:
    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    reader = dcdal.DALReader(connection=conn)
    metadata_query = psycopg.sql.SQL(
        "select n.data_source_id, nvt.value_type_id, nvt.table_name, nvt.column_name "
        "from preprocessed_raw_data.data_sources n "
        "join preprocessed_raw_data.data_source_value_types nvt on n.value_type_id = "
        "nvt.value_type_id "
        "where n.has_value = True "
        "  and n.data_source_id = any(%(data_source_id_list)s) "
    )
    metadata_df = pd.DataFrame(
        data=conn.execute(
            metadata_query,
            query_parameters={"data_source_id_list": data_source_id_list},
            fetchable=True,
        )
    )
    if metadata_df.empty:
        return {}

    intermediate_data = {}
    try:
        for i, data_type in (
                metadata_df.groupby(
                    by=["value_type_id", "table_name", "column_name"])["data_source_id"].agg(list).reset_index().iterrows()):
            intermediate_data[data_type["value_type_id"]] = reader.read_table_to_dataframe(
                schema="preprocessed_raw_data",
                table=data_type["table_name"],
                conditions=[
                    f"data_source_id = any(array{data_type['data_source_id']}::bigint[])",
                    f"timestamp between '{start_time}'::timestamp and '{end_time}'::timestamp",
                ],
                columns=["data_source_id", "timestamp", data_type["column_name"]],
            ).groupby("data_source_id")

    except KeyError as e:
        print(f"Key error: {e}")
        return {}

    data_sources_object = {}
    for i, metadata_row in metadata_df.iterrows():
        data_sources_object[metadata_row["data_source_id"]] = (
            intermediate_data[metadata_row["value_type_id"]]
            .get_group(metadata_row["data_source_id"])
            .loc[:, ["timestamp", "value"]]
        )

    return data_sources_object


def read_ingestion_data_from_db(machine_id):
    datasources_over_time_df = df_from_db(
        schema='dashboards',
        table='data_sources_with_data_per_hour',
        columns=[
            "timestamp",
            "num_data_sources",
            "list_of_data_sources"
        ],
        conditions=[f"machine_id = {int(machine_id)}"]
    )

    return datasources_over_time_df


def get_ingestion_rates(machines_names):
    ingestion_object = {}
    for machine in machines_names:
        machine_id = get_machine_id_by_name(machine)
        ingestion_object[machine_id] = read_ingestion_data_from_db(machine_id)
    return ingestion_object


def load_data_sources_connections(machines):
    data_sources_connections_df = df_from_db(
        schema="preprocessed_raw_data",
        table="data_sources_connections_v",
        columns=[
            "data_source_actual_value",
            "data_source_nominal_value",
            "data_source_standby_value",
            "machine_id"
        ]
    )

    return data_sources_connections_df
