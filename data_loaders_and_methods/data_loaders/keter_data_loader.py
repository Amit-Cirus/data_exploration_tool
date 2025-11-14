import pandas as pd

import pytz as pytz

from src.data_loaders.algo.keter_algorithmic_events_data import load_predicted_events
from src.data_loaders.keter_labeled_events import load_labeled_categories
from src.data_loaders.keter_manual_events import load_manual_events_from_db, load_manual_events_from_csv
from src.data_loaders.keter_pipelines_versions_loader import get_pipeline_versions
from src.data_loaders.keter_raw_data import get_ingestion_rates, load_data_sources_connections
from src.data_loaders.keter_statistical_data import load_metadata
from src.keter_globals import *

from loguru import logger as log

target_tz = 'Asia/Jerusalem'


def initialize_data_object(data_object, machines, only_manual_mode):
    if only_manual_mode:
        log.warning('Only manual mode is set')
        return

    data_object["data_sources_metadata"] = load_metadata(
        machines,
        data_object["configurations"]["pipeline_versions"]["stats_pipe_version"]
    )

    data_object["ingestion_rates"] = get_ingestion_rates(machines)

    is_db_used = data_object['configurations']['manual_tagging']['use_db']
    reading_manual_events_function = load_manual_events_from_db if is_db_used else load_manual_events_from_csv

    labeled_events_pipe_version = data_object["configurations"]["pipeline_versions"]["labeled_events_pipe_version"]
    if labeled_events_pipe_version != 'manual':
        data_object["events"]['labeled'] = load_labeled_categories(
            machines=machines,
            labeled_events_pipe_version=labeled_events_pipe_version,
            before_hours=
            data_object["configurations"]["time_configurations"]["show_before_event"],
            after_hours=data_object["configurations"]["time_configurations"]["show_after_event"],
        )

    data_object["events"]['manual'] = reading_manual_events_function(
        before_hours=data_object["configurations"]["time_configurations"]["show_before_event"],
        after_hours=data_object["configurations"]["time_configurations"]["show_after_event"],
        load_deprecated=data_object["configurations"]["manual_tagging"]["show_deprecated"])

    predicted_events_pipe_version = data_object["configurations"]["pipeline_versions"]["events_pipe_version"]
    if predicted_events_pipe_version != 'manual':
        data_object['algo']['predicted_events'] = load_predicted_events(
            machines=machines,
            pred_events_pipe_version=
            data_object["configurations"][
                "pipeline_versions"]["events_pipe_version"],
            before_hours=data_object["configurations"][
                "time_configurations"]["show_before_event"],
            after_hours=data_object["configurations"][
                "time_configurations"]["show_after_event"]
        )

    data_object['preprocessed_raw_data'] = dict()
    data_object['preprocessed_raw_data']['data_sources_connections_v'] = load_data_sources_connections(machines=machines)


def try_parsing_date(text):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            parsed_date = datetime.strptime(text, fmt)
            if fmt == "%Y-%m-%dT%H:%M:%S.%fZ":
                # Assume the parsed date is in UTC
                parsed_date = parsed_date.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(target_tz))
            else:
                # Assume the parsed date is already in the target timezone
                parsed_date = pytz.timezone(target_tz).localize(parsed_date)

            return parsed_date
        except ValueError:
            pass
    raise ValueError("no valid date format found")


def make_timestamp_tz_naive(dt):
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def get_event_metadata(internal_event_id, events_df):
    relevant_print_row = events_df[events_df["internal_event_id"] == internal_event_id]
    event_start_time = pd.Timestamp(relevant_print_row["start_timestamp"].values[0])
    event_end_time = pd.Timestamp(relevant_print_row["end_timestamp"].values[0])

    event_type = relevant_print_row["label_name"].values[0] if 'label_name' in events_df.columns else "Predicted"
    return event_start_time, event_end_time, event_type


def get_event_id_str(machine_events):
    return f"/{len(machine_events)}:"


def get_event_type_str(machine_events, internal_event_id):
    if machine_events.empty:
        return "No events to show"
    if 'username' in machine_events.columns:
        string_to_show = f"  Type - {machine_events['label_name'].values[internal_event_id]}; " \
                         f"Tagger - {machine_events['username'].values[internal_event_id]}; "
        if machine_events['is_deprecated'].values[internal_event_id]:
            string_to_show += "Deprecated"
        return string_to_show

    if 'label_name' in machine_events.columns:
        return f"  Type - {machine_events['label_name'].values[internal_event_id]}"
    return f"   Total num anomalies - {machine_events['num_anomalies'].values[internal_event_id]}"


def update_config(data_object):
    try:
        pipeline_versions_options = get_pipeline_versions()
    except Exception as e:
        log.error(f"No connection to DB and NetApp, only manual upload is available\n Exception - {e}")
        pipeline_versions_options = {'stats_pipe_options': ['manual'],
                                     'labeled_events_pipe_options': ['manual'],
                                     'training_pipe_options': ['manual'],
                                     'events_pipe_options': ['manual']}

    data_object['configurations']["pipeline_versions_options"] = pipeline_versions_options
    data_object['configurations']["pipeline_versions"] = {
        "stats_pipe_version": pipeline_versions_options["stats_pipe_options"][0],
        "labeled_events_pipe_version": pipeline_versions_options["labeled_events_pipe_options"][0],
        "training_pipe_version": pipeline_versions_options["training_pipe_options"][0],
        "events_pipe_version": pipeline_versions_options["events_pipe_options"][0],
    }
