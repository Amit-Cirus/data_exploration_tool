import base64
import io
import pathlib
from datetime import timedelta
import os

import pandas as pd

import dcdal

from src.data_loaders.keter_raw_data import get_machine_id_by_name

from src.keter_globals import *
import src.logic.utilities as utils


def get_event_types_df():
    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    reader = dcdal.DALReader(connection=conn)
    events_labels_df = reader.read_table_to_dataframe(
        schema="events",
        table="labeled_event_types",
        columns=[
            "event_type_id",
            "event_type_name"
        ],
    )
    conn.close()
    return events_labels_df


def generate_random_events_df(start_timestamp=full_start_timestamp,
                              end_timestamp=full_end_timestamp,
                              num_events=10):
    import random
    from datetime import timedelta
    events_df = pd.DataFrame(columns=["event_id", "start_timestamp", "end_timestamp", "event_type"])
    start_timestamps = [start_timestamp + (end_timestamp - start_timestamp) * random.random() for _ in range(num_events)]
    events_df["event_id"] = [i + 1 for i in range(num_events)]
    events_df["start_timestamp"] = start_timestamps
    events_df["end_timestamp"] = events_df["start_timestamp"] + timedelta(minutes=random.randint(5, 30))
    events_df["event_type_id"] = [5 for _ in range(num_events)]
    events_df["label_name"] = ["No data" for _ in range(num_events)]
    events_df = events_df.sort_values("start_timestamp")
    return events_df


def generate_no_data_events_df():
    events_df = pd.DataFrame(columns=["event_id", "start_timestamp", "end_timestamp", "event_type"])
    events_df["event_id"] = [1]
    events_df["start_timestamp"] = [full_start_timestamp]
    events_df["end_timestamp"] = [full_end_timestamp]
    events_df["event_type_id"] = [5]
    events_df["label_name"] = ["No data"]
    return events_df


def get_labeled_category_from_csv(machine_id):
    machine_file_name = os.path.join(os.getcwd(), "temporary_data", f"machine_{machine_id}_events_category.csv")
    events_df = pd.read_csv(machine_file_name, usecols=["start_time", "end_time", "category", "category_str"])
    events_df["start_timestamp"] = utils.to_pd_datetime(events_df["start_time"])
    events_df["end_timestamp"] = utils.to_pd_datetime(events_df["end_time"])
    events_df["event_id"] = [i + 1 for i in range(len(events_df))]
    events_df["event_type"] = events_df['category'].tolist()  # [1 for _ in range(len(events_df))] #TODO CAST INT
    events_df['label_name'] = events_df['category_str']
    return events_df


def get_labeled_category_from_df(labeled_events_df, before_hours, after_hours, machines):
    labeled_events_df["start_timestamp"] = utils.to_pd_datetime(labeled_events_df["start_timestamp"])
    labeled_events_df["end_timestamp"] = utils.to_pd_datetime(labeled_events_df["end_timestamp"])

    event_types_df = pd.DataFrame(
        {'event_type_id': [0, 1, 2, 3, 4, 5, 6],
         'event_type_name': ["Good", "Machine stop", "Pre event", "Short cycle", "Long cycle", "No data",
                             "Defective parts"],
         })
    labeled_events_df['label_name'] = labeled_events_df['event_type_id'].map(
        event_types_df.set_index('event_type_id')['event_type_name'])

    labeled_events_df["before_event_timestamp"] = labeled_events_df["start_timestamp"] - timedelta(hours=before_hours)
    labeled_events_df["after_event_timestamp"] = labeled_events_df["end_timestamp"] + timedelta(hours=after_hours)

    data_obj = {}
    machines_with_data = []
    for machine_id in machines:
        curr_labeled_events_df = labeled_events_df[labeled_events_df['machine_id'] == machine_id]
        if not curr_labeled_events_df.empty:
            machines_with_data.append(str(machine_id))
        curr_filtered_events_df = curr_labeled_events_df[curr_labeled_events_df['event_type_id'] != 0]
        data_obj[str(machine_id)] = {
            'full': curr_labeled_events_df,
            'filtered': curr_filtered_events_df
        }
    return data_obj, machines_with_data


def get_labeled_category_from_db(machine_id, labeled_events_pipe_version):
    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    reader = dcdal.DALReader(connection=conn)
    labeled_events_df = reader.read_table_to_dataframe(
        schema="events",
        table="merged_calculated_labeled_events",
        columns=[
            "event_id",
            "start_timestamp",
            "end_timestamp",
            "event_type_id"
        ],
        conditions=[f"machine_id = {machine_id}", f"run_id = {labeled_events_pipe_version}"],
    )
    conn.close()
    if not labeled_events_df.empty:
        labeled_events_df["event_type"] = labeled_events_df["event_type_id"]
        labeled_events_df['label_name'] = labeled_events_df['event_type'].map(
            get_event_types_df().set_index('event_type_id')['event_type_name'])
    return labeled_events_df


def get_labeled_events_per_datasource_from_db(machine_id, labeled_events_pipe_version):
    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    reader = dcdal.DALReader(connection=conn)
    labeled_events_per_datasource_df = reader.read_table_to_dataframe(
        schema="events",
        table="calculated_labeled_events_per_data_source",
        columns=[
            "event_id",
            "start_timestamp",
            "end_timestamp",
            "event_type_id",
            "data_source_id"
        ],
        conditions=[f"machine_id = {machine_id}", f"run_id = {labeled_events_pipe_version}"],
    )
    conn.close()
    if not labeled_events_per_datasource_df.empty:
        labeled_events_per_datasource_df["event_type"] = labeled_events_per_datasource_df["event_type_id"]
        labeled_events_per_datasource_df['label_name'] = labeled_events_per_datasource_df['event_type'].map(
            get_event_types_df().set_index('event_type_id')['event_type_name'])
    return labeled_events_per_datasource_df


def load_labeled_categories(machines, labeled_events_pipe_version, before_hours, after_hours):
    curr_data_object = {}
    for machine_name in machines:
        machine_id = get_machine_id_by_name(machine_name)
        events_df = get_labeled_category_from_db(machine_id, labeled_events_pipe_version)
        events_per_datasource_df = get_labeled_events_per_datasource_from_db(machine_id, labeled_events_pipe_version)
        if events_df.empty:
            print(f"Warning: Machine {machine_name} has no data, generating one 'no data' event")
            events_df = generate_no_data_events_df()

        events_df["before_event_timestamp"] = events_df["start_timestamp"] - timedelta(hours=before_hours)
        events_df["after_event_timestamp"] = events_df["end_timestamp"] + timedelta(hours=after_hours)

        filtered_events_df = events_df[events_df['event_type_id'] != 0]
        curr_data_object[machine_id] = {
            'full': events_df,
            'filtered': filtered_events_df,
            'per_data_source': events_per_datasource_df
        }
    return curr_data_object


def parse_manual_labeled_events_contents(contents, filenames, machines, before_hours, after_hours):
    dfs = []
    for content, filename in zip(contents, filenames):
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        try:
            file_extension = pathlib.Path(filename).suffix
            if file_extension == '.csv':
                curr_df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                dfs.append(curr_df)
            else:
                print(f"Error: There is no implementation for extension {file_extension}")
        except Exception as e:
            print(e)

    full_df = pd.concat(dfs, axis=0)
    data_obj, machines_with_data = get_labeled_category_from_df(full_df, before_hours, after_hours, machines)
    return data_obj, machines_with_data
