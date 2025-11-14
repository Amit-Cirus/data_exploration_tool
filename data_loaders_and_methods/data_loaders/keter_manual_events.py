from datetime import timedelta
import os

import pandas as pd

import dcdal

from src.keter_globals import *
import src.logic.utilities as utils


def load_manual_events_from_csv(before_hours, after_hours, load_deprecated=False):
    manual_events_file = os.path.join("temporary_data", "manual_events.csv")
    if os.path.exists(manual_events_file):
        manual_events_df = pd.read_csv(manual_events_file)
        manual_events_df['start_timestamp'] = pd.to_datetime(manual_events_df['start_timestamp'],
                                                             format="%Y-%m-%d %H:%M:%S.%f")
        manual_events_df['end_timestamp'] = pd.to_datetime(manual_events_df['end_timestamp'],
                                                           format="%Y-%m-%d %H:%M:%S.%f")
        manual_events_df["before_event_timestamp"] = manual_events_df["start_timestamp"] - timedelta(hours=before_hours)
        manual_events_df["after_event_timestamp"] = manual_events_df["end_timestamp"] + timedelta(hours=after_hours)
        manual_events_df["label_name"] = "Manual"
        if not load_deprecated:
            manual_events_df = manual_events_df[not manual_events_df['is_deprecated']]
    else:
        manual_events_df = pd.DataFrame(columns=manual_events_columns)
    return manual_events_df


def load_manual_events_from_db(before_hours, after_hours, load_deprecated=False):
    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    reader = dcdal.DALReader(connection=conn)

    manual_events_df = reader.read_table_to_dataframe(
        schema="algo",
        table=f"manually_tagged_events",
        columns=['event_id'] + manual_events_columns,
    )
    conn.close()

    if not manual_events_df.empty:
        if not load_deprecated:
            manual_events_df = manual_events_df[manual_events_df['is_deprecated'] == False]
        manual_events_df['start_timestamp'] = utils.to_pd_datetime(manual_events_df['start_timestamp'], dt_format="%Y-%m-%d %H:%M:%S.%f")
        manual_events_df['end_timestamp'] = utils.to_pd_datetime(manual_events_df['end_timestamp'], dt_format="%Y-%m-%d %H:%M:%S.%f")
        manual_events_df["before_event_timestamp"] = manual_events_df["start_timestamp"] - timedelta(hours=before_hours)
        manual_events_df["after_event_timestamp"] = manual_events_df["end_timestamp"] + timedelta(hours=after_hours)
        manual_events_df["label_name"] = "Manual"
    return manual_events_df


def add_manual_event_to_csv(machine_id, data_source_ids, start_timestamp, end_timestamp, username, insert_timestamp,
                            pipelines_configurations):
    manual_event_values = ["Manual",
                           int(machine_id),
                           data_source_ids,
                           start_timestamp,
                           end_timestamp,
                           username,
                           insert_timestamp,
                           pipelines_configurations]
    row = dict(zip(manual_events_columns, manual_event_values))
    # TODO: Check if exists first
    manual_events_df = load_manual_events_from_csv(3, 1)
    manual_events_df = manual_events_df.append(row, ignore_index=True)

    manual_events_file = os.path.join("temporary_data", "manual_events.csv")
    manual_events_df.to_csv(manual_events_file, index=False)
    return manual_events_df


def remove_manual_event_from_csv(machine_id, start_timestamp, end_timestamp, username, event_id):
    print(f"Manually tagged event {event_id} will be marked as deprecated")

    manual_events_df = load_manual_events_from_csv(3, 1)
    mask = ((manual_events_df['machine_id'] == int(machine_id)) &
            (manual_events_df['username'] == username) &
            (manual_events_df['start_timestamp'] == start_timestamp) &
            (manual_events_df['end_timestamp'] == end_timestamp))

    if mask.sum() == 1:
        manual_events_df.loc[mask, 'is_deprecated'] = True
        manual_events_file = os.path.join("temporary_data", "manual_events.csv")
        manual_events_df.to_csv(manual_events_file, index=False)
    return manual_events_df


def get_manual_events_per_machine(manual_events_df, machine_id):
    if manual_events_df.empty:
        return pd.DataFrame(columns=manual_events_columns)
    relevant_events_df = manual_events_df[manual_events_df['machine_id'] == int(machine_id)]
    if relevant_events_df.empty:
        return pd.DataFrame(columns=manual_events_columns)
    else:
        return relevant_events_df


def add_manual_event_to_db(machine_id, data_source_ids, start_timestamp, end_timestamp, username, insert_timestamp,
                           pipelines_configurations):
    manual_event_values = ["Manual",
                           int(machine_id),
                           data_source_ids,
                           start_timestamp,
                           end_timestamp,
                           username,
                           insert_timestamp,
                           pipelines_configurations,
                           False]
    row = dict(zip(manual_events_columns, manual_event_values))

    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    writer = dcdal.DALWriter(connection=conn)

    writer.add_row_to_table(schema="algo",
                            table=f"manually_tagged_events",
                            data=row)

    conn.close()


def remove_manual_event_from_db(machine_id, start_timestamp, end_timestamp, username, event_id):
    print(f"Manually tagged event {event_id} will be marked as deprecated")

    conn = dcdal.DALConnection(
        host=os.environ["DB_HOST"],
        db=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )

    reader = dcdal.DALReader(connection=conn)
    relevant_manual_labels_df = reader.read_table_to_dataframe(schema="algo",
                                                               table=f"manually_tagged_events",
                                                               conditions=[f"machine_id ={int(machine_id)}",
                                                                           f"start_timestamp = '{start_timestamp}'",
                                                                           f"end_timestamp = '{end_timestamp}'",
                                                                           f"username = '{username}'"]
                                                               )
    if len(relevant_manual_labels_df) == 1:
        writer = dcdal.DALWriter(connection=conn)
        writer.update_rows(schema="algo",
                           table=f"manually_tagged_events",
                           data=dict(zip(['is_deprecated'], [True])),
                           conditions=[f"machine_id ={int(machine_id)}",
                                       f"start_timestamp = '{start_timestamp}'",
                                       f"end_timestamp = '{end_timestamp}'",
                                       f"username = '{username}'"])
    else:
        print(f"Too much data is fitting the conditions, aborting untagging of event {event_id}")

    conn.close()
