import json
import time
from datetime import timedelta

import dash
import numpy
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, no_update, callback_context
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Serverside

from src.data_loaders.algo.keter_algorithmic_events_data import (
    filter_relevant_predicted_events,
    get_data_sources_contributions_to_events,
    get_severity_events_from_db,
    get_predicted_anomalies_from_db,
    get_predicted_anomalies_from_csv
)
from src.data_loaders.algo.keter_algorithmic_reconstruction_data import (
    load_algorithmic_results_data,
    load_algorithmic_results_data_multi
)
from src.data_loaders.keter_data_loader import (
    get_event_metadata,
    get_event_type_str,
    get_event_id_str,
    try_parsing_date,
)
from src.data_loaders.keter_manual_events import (
    get_manual_events_per_machine,
    add_manual_event_to_db,
    add_manual_event_to_csv,
    load_manual_events_from_csv,
    load_manual_events_from_db,
    remove_manual_event_from_db,
    remove_manual_event_from_csv
)
from src.data_loaders.keter_pipelines_versions_loader import (
    get_training_version_from_name
)
from src.data_loaders.keter_raw_data import (
    load_data,
    get_machine_id_by_name,
    get_data_source_id_by_name,
    get_data_sources_by_machine,
    get_data_sources_names,
)
from src.keter_globals import *
from src.plotting_utils import (
    create_figure,
    plot_raw_data_sources,
    plot_algo_data_sources,
    plot_events,
    plot_predicted_events,
    plot_anomalies, plot_events_datasource
)
from src.widgets.data_sources_widgets_creation import (
    create_sidebar_metadata,
    create_plot_element_children,
    create_static_plot_element_children,
    TRACEUPDATER_ID,
    STORE_ID,
    GRAPH_ID,
    OVERVIEW_GRAPH_ID,
)


def get_data_sources_connections_dict(data_object, machine_id, data_source_ids):
    result_dict = {}
    df = data_object['preprocessed_raw_data']['data_sources_connections_v']
    if df.empty or not data_source_ids:
        return result_dict

    for actual_id in data_source_ids:
        if actual_id in df['data_source_actual_value'].values:
            filtered_df = df[(df['machine_id'] == int(machine_id)) & (df['data_source_actual_value'] == actual_id)]

            if not filtered_df.empty:
                matching_nominal_id = filtered_df.iloc[0]['data_source_nominal_value']
                matching_standby_id = filtered_df.iloc[0]['data_source_standby_value']
                result_dict[actual_id] = {'data_source_nominal_value': matching_nominal_id,
                                          'data_source_standby_value': matching_standby_id}
            else:
                result_dict[actual_id] = {'data_source_nominal_value': None, 'data_source_standby_value': None}
        else:
            result_dict[actual_id] = {'data_source_nominal_value': None, 'data_source_standby_value': None}

    return result_dict


def load_data_sources_data(data_object, machine_id, start_timestamp, end_timestamp, data_source_ids=None):
    # Load data sources data:
    data_object["data_sources_values"][machine_id] = load_data(data_source_ids, start_timestamp, end_timestamp)

    # Load data sources connections data:
    data_object["data_sources_connections_values"] = dict()
    data_sources_connections_dict = get_data_sources_connections_dict(data_object, machine_id, data_source_ids)
    data_source_nominal_ids = [int(source_connections['data_source_nominal_value'])
                               for source_connections in data_sources_connections_dict.values() if
                               source_connections['data_source_nominal_value'] is not None]
    data_object["data_sources_connections_values"][machine_id] = load_data(data_source_nominal_ids, start_timestamp,
                                                                           end_timestamp)

    data_object["selected_machine"] = machine_id
    data_object["start_time"] = start_timestamp
    data_object["end_time"] = end_timestamp


def load_data_sources_predictions(data_object, machine_id, start_timestamp, end_timestamp, is_scaled=False,
                                  data_source_ids=None):
    alg_name = ''
    meta_experiment_slug = \
        get_training_version_from_name(data_object["configurations"]["pipeline_versions"]["training_pipe_version"])
    load_reconstruction_func = load_algorithmic_results_data_multi \
        if data_object["configurations"]["reading_files_multi"] else load_algorithmic_results_data
    data_object["algo"]["reconstruction"][machine_id] = load_reconstruction_func(
        meta_experiment_slug=meta_experiment_slug,
        data_source_ids=data_source_ids,
        alg_name=alg_name,
        is_scaled=is_scaled,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,

    )
    data_object["algorithms"] = reconstruction_algorithms


def fill_figure_with_data(data_object, figure, selected_values_dict):
    machine_id = selected_values_dict["machine_id"]
    analyzed_data_sources = selected_values_dict["selected_data_sources"]
    draw_reconstruction = selected_values_dict["show_algo_reconstruction"]
    selected_algorithms = selected_values_dict["selected_algorithms"]
    curr_plot_num = 1

    plot_raw_data_sources(figure,
                          curr_plot_num,
                          machine_id,
                          analyzed_data_sources,
                          data_object,
                          draw_reconstruction)
    if draw_reconstruction:
        curr_plot_num = 1
        curr_plot_num = plot_algo_data_sources(figure,
                                               curr_plot_num,
                                               machine_id,
                                               analyzed_data_sources,
                                               data_object,
                                               selected_algorithms)


def plot_anomalies_and_events(figure, data_object, selected_values_dict, subplot_names):
    machine_id = selected_values_dict["machine_id"]
    start_date = selected_values_dict["start_time"]
    end_date = selected_values_dict["end_time"]
    analyzed_data_sources = selected_values_dict["selected_data_sources"]
    draw_labeled_events = selected_values_dict["draw_labeled_events"]
    selected_labeled_events_types = selected_values_dict["selected_labeled_events_types"]
    draw_predicted_events = selected_values_dict["draw_predicted_events"]
    draw_manual_events = selected_values_dict["draw_manual_events"]
    draw_predicted_anomalies = selected_values_dict["draw_predicted_anomalies"]
    draw_reconstruction = selected_values_dict["show_algo_reconstruction"]
    selected_algorithms = selected_values_dict["selected_algorithms"]

    if draw_predicted_anomalies and 'selected_event_anomalies' in data_object:
        curr_plot_num = 1
        plot_anomalies(figure,
                       curr_plot_num,
                       machine_id,
                       analyzed_data_sources,
                       data_object,
                       selected_algorithms,
                       draw_reconstruction=draw_reconstruction,
                       draw_raw_anomalies=not draw_reconstruction and draw_predicted_anomalies)

    real_start_date = selected_values_dict["start_time"] + timedelta(
        hours=data_object["configurations"]["time_configurations"]["show_before_event"])
    real_end_date = selected_values_dict["end_time"] - timedelta(
        hours=data_object["configurations"]["time_configurations"]["show_after_event"])

    if draw_predicted_events:
        predicted_events = data_object["algo"]['predicted_events'][machine_id]['events']
        print("  Adding predicted events to the graphs")
        if 'load_by_dates' in data_object and data_object['load_by_dates']:
            plot_predicted_events(
                figure,
                subplot_names,
                predicted_events,
                real_start_date,
                real_end_date,
                selected_event=None,
                severities=None,
                opacity_rate=event_opacity_rate,
                color=predicted_event_color
            )
        else:
            start_times = [start_date, real_start_date, real_end_date]
            end_times = [real_start_date, real_end_date, end_date]
            colors = [out_of_scope_predicted_event_color, predicted_event_color, out_of_scope_predicted_event_color]
            severities_list = [None, data_object["selected_event_severities"], None]
            for start_ts, end_ts, color, severities in zip(start_times, end_times, colors, severities_list):
                plot_predicted_events(
                    figure,
                    subplot_names,
                    predicted_events,
                    start_ts,
                    end_ts,
                    selected_event=data_object['selected_event'],
                    severities=severities,
                    opacity_rate=event_opacity_rate,
                    color=color
                )
    if draw_labeled_events:
        filtered_labeled_events = data_object["events"]['labeled'][machine_id]['filtered']
        mask = filtered_labeled_events['label_name'].isin(selected_labeled_events_types)
        filtered_labeled_events = filtered_labeled_events[mask]
        plot_events(
            figure,
            subplot_names,
            filtered_labeled_events,
            start_date,
            end_date,
            opacity_rate=event_opacity_rate,
            color=None
        )

    if draw_manual_events:
        print("  Adding manual events to the graphs")
        manual_events = get_manual_events_per_machine(data_object["events"]['manual'], machine_id)

        # Retrieve rows where 'int_list' is equal to 'target_list'
        data_source_ids = [
            int(get_data_source_id_by_name(data_source_name))
            for data_source_name in analyzed_data_sources
        ]
        manual_events = manual_events[manual_events['data_sources_list'].apply(lambda x: x == data_source_ids)]
        curr_user = data_object['configurations']['manual_tagging']['username']
        plot_events(
            figure,
            subplot_names,
            manual_events[manual_events['username'] == curr_user],
            start_date,
            end_date,
            opacity_rate=event_opacity_rate,
            color=manual_event_color
        )
        plot_events(
            figure,
            subplot_names,
            manual_events[manual_events['username'] != curr_user],
            start_date,
            end_date,
            opacity_rate=event_opacity_rate,
            color=out_of_scope_manual_event_color
        )


def plot_events_per_datasource(figure, data_object, selected_values_dict, subplot_names):
    machine_id = selected_values_dict["machine_id"]
    start_date = selected_values_dict["start_time"]
    end_date = selected_values_dict["end_time"]
    selected_labeled_events_types = selected_values_dict["selected_labeled_events_types"]
    analyzed_data_sources = selected_values_dict["selected_data_sources"]
    draw_labeled_events = selected_values_dict["draw_labeled_events"]

    data_source_ids = [
        int(get_data_source_id_by_name(data_source))
        for data_source in analyzed_data_sources
    ]

    if draw_labeled_events:
        labeled_event_per_datasource = data_object["events"]['labeled'][machine_id]['per_data_source']
        if len(labeled_event_per_datasource) != 0:
            mask = labeled_event_per_datasource['label_name'].isin(selected_labeled_events_types)
            labeled_events_per_datasource = labeled_event_per_datasource[mask]
            for data_source_id in data_source_ids:
                curr_labeled_events_per_datasource = labeled_events_per_datasource[
                    labeled_events_per_datasource['data_source_id'] == data_source_id]
                curr_subplot_names = [plot_name for plot_name in subplot_names if str(data_source_id) in plot_name]
                if not curr_labeled_events_per_datasource.empty:
                    plot_events_datasource(
                        figure,
                        subplot_names,
                        curr_subplot_names,
                        curr_labeled_events_per_datasource,
                        start_date,
                        end_date,
                        opacity_rate=event_opacity_rate,
                        color=None
                    )


def create_graph_content(data_object,
                         machine_name,
                         start_timestamp,
                         end_timestamp,
                         analyzed_data_sources,
                         draw_labeled_events,
                         selected_labeled_events_types,
                         draw_predicted_anomalies,
                         draw_predicted_events,
                         draw_manual_events,
                         show_reconstruction_results,
                         is_scaled=False):
    print("Plotting required data:")
    if len(analyzed_data_sources) > 0:
        print(
            f"  Entering update phase for {len(analyzed_data_sources)} data sources: {','.join(analyzed_data_sources)}"
        )
    start = time.time()
    machine_id = get_machine_id_by_name(machine_name)
    data_source_ids = [
        int(get_data_source_id_by_name(data_source))
        for data_source in analyzed_data_sources
    ]

    start_ts = try_parsing_date(start_timestamp) - timedelta(
        hours=data_object['configurations']['time_configurations']['show_before_event'])
    end_ts = try_parsing_date(end_timestamp) + timedelta(
        hours=data_object['configurations']['time_configurations']['show_after_event'])

    load_data_sources_data(
        data_object=data_object,
        machine_id=machine_id,
        start_timestamp=start_ts,
        end_timestamp=end_ts,
        data_source_ids=data_source_ids,
    )

    if data_object["data_sources_values"][machine_id] == {}:
        print(f"      No raw data for machine {machine_id} and {','.join([str(idx) for idx in data_source_ids])} between {start_ts} and {end_ts}")
        return None, None, None, None, None

    if show_reconstruction_results:
        training_pipe_version = data_object['configurations']['pipeline_versions']['training_pipe_version']
        if training_pipe_version != 'manual':
            load_data_sources_predictions(data_object=data_object,
                                          machine_id=machine_id,
                                          start_timestamp=start_ts,
                                          end_timestamp=end_ts,
                                          is_scaled=is_scaled,
                                          data_source_ids=data_source_ids)

    if 'selected_event_anomalies_models' in data_object:
        selected_algorithms = data_object['selected_event_anomalies_models']
    else:
        if show_reconstruction_results:
            selected_algorithms = {}
            keys = data_source_ids
            for key in keys:
                selected_algorithms[key] = list(data_object['algo']['reconstruction'][machine_id][key].keys())
        else:
            selected_algorithms = {}

    print(f"    Loading data took {str(timedelta(seconds=time.time() - start))}")
    if show_reconstruction_results:
        algo_dict = data_object["algo"]["reconstruction"][machine_id]
        if algo_dict is not None and all(value == {} for value in algo_dict.values()):
            show_reconstruction_results = False
            # TODO: Show notification to user
            print(
                f"      No algorithms results for machine {machine_id} and {','.join([str(idx) for idx in data_source_ids])}")
    start_plot = time.time()
    draw_predicted_events_severities = False  # TODO: Activate feature
    plotting_parameters = {
        "machine_id": machine_id,
        "start_time": start_ts,
        "end_time": end_ts,
        "selected_data_sources": analyzed_data_sources,
        "show_timeseries_stats": False,
        "show_algo_reconstruction": show_reconstruction_results,
        "draw_labeled_events": draw_labeled_events,
        "selected_labeled_events_types": selected_labeled_events_types,
        "draw_predicted_events": draw_predicted_events,
        "draw_predicted_events_severities": draw_predicted_events_severities,
        "draw_manual_events": draw_manual_events,
        "draw_predicted_anomalies": draw_predicted_anomalies,
        "selected_algorithms": selected_algorithms,
        "load_by_dates": 'load_by_dates' in data_object and data_object['load_by_dates']
    }

    # This chunk of code handles showing anomalies when "Load by dates" is activated
    load_by_dates = plotting_parameters["load_by_dates"]
    pred_events_pipe_version = data_object["configurations"]["pipeline_versions"]["events_pipe_version"]
    if load_by_dates and draw_predicted_anomalies:
        if pred_events_pipe_version == 'manual':
            anomalies_df = get_predicted_anomalies_from_csv(machine_id, None, start_ts, end_ts)
        else:
            anomalies_df = get_predicted_anomalies_from_db(machine_id, pred_events_pipe_version, None, start_ts, end_ts)

        data_object['selected_event_anomalies'] = anomalies_df
        selected_event_anomalies_models = {}
        for data_source in list(anomalies_df['data_source_id'].unique()):
            selected_event_anomalies_models[data_source] = list(
                anomalies_df[anomalies_df['data_source_id'] == data_source]['model_type'].unique())
        data_object['selected_event_anomalies_models'] = selected_event_anomalies_models
        plotting_parameters['selected_algorithms'] = data_object['selected_event_anomalies_models']

    # TODO: Compare previous fig and current - curr_selected_valuses vs data_object["selected_values"]
    # TODO: and activate only if relevant
    fig, num_plots, subplot_names = create_figure(data_object, plotting_parameters)
    plotting_parameters['num_plots'] = num_plots
    fill_figure_with_data(data_object, fig, plotting_parameters)

    data_object["selected_values"] = plotting_parameters
    try:
        coarse_fig = fig._create_overview_figure()
    except Exception as e:
        print(f"Error in creating graph overview: {e}")
        coarse_fig = None

    plot_anomalies_and_events(fig, data_object, plotting_parameters, subplot_names)
    plot_events_per_datasource(fig, data_object, plotting_parameters, subplot_names)
    print(f"    Plotting data took {str(timedelta(seconds=time.time() - start_plot))}")
    print("Finished drawing...")
    return fig, coarse_fig, {}, {}, Serverside(fig)


def get_machine_events(data_object, label_type, machine_id, predicted_filter=True):
    label_type_str = "labeled" if label_type == 1 else "predicted" if label_type == 2 else 'manual'
    if label_type == 1:
        events_df = data_object["events"][label_type_str][machine_id]['filtered']
    if label_type == 2:
        if data_object["algo"]['predicted_events'][machine_id]:
            events_df = data_object["algo"]['predicted_events'][machine_id]["events"]
            if events_df.empty:
                print(f"No predicted events to show for machine {machine_id}")
                return pd.DataFrame()
            if predicted_filter:
                events_df = filter_relevant_predicted_events(events_df,
                                                             data_object["events"]["labeled"][machine_id]['filtered'])
        else:
            print(f"No predicted events to show for machine {machine_id}")
            return pd.DataFrame()
    if label_type == 3:
        events_df = get_manual_events_per_machine(data_object["events"][label_type_str], int(machine_id))

    events_df.sort_values("start_timestamp", ascending=True, inplace=True)
    events_df['internal_event_id'] = list(range(len(events_df)))
    return events_df


def get_initial_data_sources_to_show(machine_id, data_object, relevant_anomalies_df, filter_by):
    max_data_sources_to_show = data_object['configurations']['events_configurations']['max_data_sources_to_show']
    if filter_by == 'no_filter':
        filter_list = data_object["selected_machine_events"]['data_sources_list'].values[
            data_object['internal_event_id']]
        filter_list = [str(curr_data_source) for curr_data_source in filter_list]
    else:
        filter_list = get_data_sources_contributions_to_events(relevant_anomalies_df, contribution_type=filter_by)
    filter_list = filter_list[:max_data_sources_to_show]

    data_sources_list = get_data_sources_names(get_data_sources_by_machine(machine_id), filter_list)
    return data_sources_list


def update_event_id(labels_type, data_object, machine_id, new_internal_event_id, selected_machine_events):
    data_object['internal_event_id'] = new_internal_event_id
    data_object['selected_event_internal'] = new_internal_event_id if new_internal_event_id < len(
        selected_machine_events) else 0
    data_object['selected_event'] = selected_machine_events["event_id"].values[data_object['selected_event_internal']]
    start_date_dt, end_date_dt, event_type = get_event_metadata(data_object['selected_event_internal'],
                                                                selected_machine_events)

    hours_before_event = data_object['configurations']['time_configurations']['show_before_event']
    hours_after_event = data_object['configurations']['time_configurations']['show_after_event']
    window_start_date = start_date_dt - timedelta(hours=hours_before_event)
    window_end_date = end_date_dt + timedelta(hours=hours_after_event)

    pred_events_pipe_version = data_object["configurations"]["pipeline_versions"]["events_pipe_version"]
    event_id = data_object['selected_event']
    if labels_type == 2:
        selected_anomalies_ids = selected_machine_events["anomaly_id_list"].values[
            data_object['selected_event_internal']]
        data_object['selected_anomalies_ids'] = selected_anomalies_ids

        if pred_events_pipe_version == 'manual':
            anomalies_df = get_predicted_anomalies_from_csv(
                machine_id,
                selected_anomalies_ids,
                window_start_date,
                window_end_date)
        else:
            anomalies_df = get_predicted_anomalies_from_db(
                machine_id,
                pred_events_pipe_version,
                selected_anomalies_ids,
                window_start_date, window_end_date)

        if not anomalies_df.empty:
            data_object['algo']['predicted_events'][machine_id]['anomalies'][event_id] = anomalies_df
            data_object['selected_event_anomalies'] = anomalies_df

        if pred_events_pipe_version != 'manual':
            severity_df = get_severity_events_from_db(event_id)
        else:
            severity_df = None
        data_object['algo']['predicted_events'][machine_id]['severity_events'] = severity_df
        data_object['selected_event_severities'] = severity_df

        if not anomalies_df.empty:
            selected_event_anomalies_models = {}
            for data_source in list(anomalies_df['data_source_id'].unique()):
                selected_event_anomalies_models[data_source] = list(
                    anomalies_df[anomalies_df['data_source_id'] == data_source]['model_type'].unique())
            data_object['selected_event_anomalies_models'] = selected_event_anomalies_models
    else:
        if pred_events_pipe_version == 'manual':
            anomalies_df = get_predicted_anomalies_from_csv(machine_id, None, window_start_date, window_end_date)
        else:
            anomalies_df = get_predicted_anomalies_from_db(machine_id, pred_events_pipe_version, None, window_start_date,
                                                           window_end_date)

        data_object.pop('selected_anomalies_ids', 'No Key found')
        data_object.pop('selected_event_severities', 'No Key found')
        data_object.pop('selected_event_anomalies_models', 'No Key found')

    if not anomalies_df.empty:
        data_object['algo']['predicted_events'][machine_id]['anomalies'][event_id] = anomalies_df
        data_object['selected_event_anomalies'] = anomalies_df

    data_object['selected_event_type'] = event_type
    return window_start_date, window_end_date


def create_predictive_callbacks(app, data_object):
    @app.callback(
        [Output('metadata-div', 'children', allow_duplicate=True),
         Output('plot-element', 'children', allow_duplicate=True),
         Output('plot-element-static', 'children', allow_duplicate=True),
         Output('load-raw-data', 'disabled', allow_duplicate=True),
         Output('load-events-data', 'disabled', allow_duplicate=True)],
        Input("machine-dropdown", "value"),

    )
    def reset_view_for_machine(machine_name):
        return [], create_plot_element_children(), create_static_plot_element_children(), False, False

    @app.callback(
        [Output('show-raw-data', 'disabled')],
        Input("data-sources-checklist", "value"),
    )
    def enable_when_selected_data_sources(selected_data_sources):
        if len(selected_data_sources) > 0:
            return False
        return True

    @app.callback(
        [Output('event-id-input', 'disabled')],
        Input("navigate-fast", "checked"),
    )
    def block_actions_by_fast_navigation(navigate_fast):
        return navigate_fast

    @app.callback(
        [
            Output('date-time-picker', 'startDate', allow_duplicate=True),
            Output('date-time-picker', 'endDate', allow_duplicate=True),
            Output("data-sources-checklist", 'value', allow_duplicate=True),
            Output('event-id-label', 'children', allow_duplicate=True),
            Output('event-type-label', 'children', allow_duplicate=True)
        ],
        [
            Input("event-id-input", "value"),
            State("machine-dropdown", "value"),
            State("checklist-labels-type", "value"),
            State("data-sources-checklist", "value")
        ]
    )
    def changed_event_id(new_event_id, machine_name, labels_type, analyzed_data_sources):
        machine_id = get_machine_id_by_name(machine_name)
        selected_machine_events = data_object['selected_machine_events']
        start_date_dt, end_date_dt = update_event_id(labels_type, data_object, machine_id, new_event_id - 1,
                                                     selected_machine_events)
        selected_machine_metadata = data_object["data_sources_metadata"][machine_id]

        filter_by = "no_filter" if labels_type == 3 else "start_timestamp"
        relevant_anomalies_df = data_object['selected_event_anomalies'] if labels_type == 2 else None
        if labels_type == 1:
            data_sources_checklist = analyzed_data_sources
        else:
            data_sources_checklist = get_initial_data_sources_to_show(machine_id,
                                                                      data_object,
                                                                      relevant_anomalies_df,
                                                                      filter_by=filter_by)

        data_source_description = get_event_type_str(selected_machine_events, data_object['selected_event_internal'])
        event_id_label = get_event_id_str(selected_machine_events)

        return start_date_dt, end_date_dt, data_sources_checklist, event_id_label, data_source_description

    @app.callback(
        [Output('navigate-fast', 'disabled'),
         Output('navigate-fast', 'checked'),
         Output('show-event-data', 'disabled')],
        Input("data-sources-checklist", "value"),
        State('navigate-fast', 'checked')
    )
    def enable_when_selected_data_sources(selected_data_sources, navigate_fast):
        if len(selected_data_sources) > 0:
            return False, navigate_fast, False
        return True, navigate_fast, True

    @app.callback(
        [
            Output('date-time-picker', 'startDate', allow_duplicate=True),
            Output('date-time-picker', 'endDate', allow_duplicate=True),
            Output("data-sources-checklist", 'value', allow_duplicate=True),
            Output('event-id-label', 'children', allow_duplicate=True),
            Output('event-type-label', 'children', allow_duplicate=True)
        ],
        [Input("checkbox-filter-pred-events", "checked"),
         State("checklist-labels-type", "value"),
         State("machine-dropdown", "value")],
        prevent_initial_call=True,

    )
    def update_predicted_events(filter_predicted_events, labels_type, machine_name):
        if labels_type == 2:
            machine_id = get_machine_id_by_name(machine_name)
            selected_machine_events = get_machine_events(data_object,
                                                         labels_type,
                                                         machine_id,
                                                         filter_predicted_events)
            data_object['selected_machine_events'] = selected_machine_events

            start_date_dt, end_date_dt = update_event_id(labels_type,
                                                         data_object,
                                                         machine_id,
                                                         data_object['internal_event_id'],
                                                         selected_machine_events)
            selected_machine_metadata = data_object["data_sources_metadata"][machine_id]
            filter_by = "start_timestamp"
            relevant_anomalies_df = data_object['selected_event_anomalies'] if labels_type == 2 else None
            data_sources_checklist = get_initial_data_sources_to_show(machine_id,
                                                                      data_object,
                                                                      relevant_anomalies_df,
                                                                      filter_by=filter_by)
            data_source_description = get_event_type_str(selected_machine_events,
                                                         data_object['selected_event_internal'])
            event_id_label = get_event_id_str(selected_machine_events)
            return start_date_dt, end_date_dt, data_sources_checklist, event_id_label, data_source_description
        return no_update

    @app.callback(
        [
            Output('metadata-div', 'children', allow_duplicate=True),
            Output('load-raw-data', 'disabled', allow_duplicate=True),
            Output('load-events-data', 'disabled', allow_duplicate=True),
        ],
        [Input('load-raw-data', 'n_clicks'),
         Input('load-events-data', 'n_clicks'),
         State("machine-dropdown", "value")
         ],
        prevent_initial_call=True,
    )
    def create_sidebar_widget(raw_data_n_clicks, events_data_n_clicks, machine_name):
        if raw_data_n_clicks == 0 and events_data_n_clicks == 0:
            return no_update

        metadata_div_children = []
        trigger = callback_context.triggered[0]
        machine_id = get_machine_id_by_name(machine_name)
        selected_machine_metadata = data_object["data_sources_metadata"][machine_id]
        selected_machine_events = get_machine_events(data_object, 1, machine_id, False)
        data_object['selected_machine_events'] = selected_machine_events
        pressed_button = trigger["prop_id"].split(".")[0]
        if pressed_button == "load-events-data":
            data_object['selected_event_internal'] = 0
            event_id = selected_machine_events['event_id'].min()
            data_object['selected_event'] = event_id
            start_date_dt, end_date_dt, event_type = \
                get_event_metadata(data_object['selected_event_internal'], selected_machine_events)
            data_object['selected_event_type'] = event_type
            metadata_div_children = create_sidebar_metadata(machine_id,
                                                            selected_machine_metadata,
                                                            selected_machine_events,
                                                            start_date_dt, end_date_dt,
                                                            "events-data")
            data_object['load_by_dates'] = False

        if pressed_button == "load-raw-data":
            metadata_div_children = create_sidebar_metadata(
                machine_id,
                selected_machine_metadata,
                None,
                full_start_timestamp, full_end_timestamp,
                "raw-data")
            data_object['load_by_dates'] = True

        return metadata_div_children, pressed_button != "load-raw-data", pressed_button != "load-events-data"

    @app.callback(
        [
            Output('metadata-div', 'children', allow_duplicate=True),
            Output("data-sources-checklist", 'value', allow_duplicate=True),
            Output("btn-tag-timeframe", "disabled", allow_duplicate=True),
            Output('plot-element', 'children', allow_duplicate=True),
            Output('plot-element-static', 'children', allow_duplicate=True),
            Output("checkbox-filter-pred-events", "style"),
            Output("btn-untag-timeframe", "style")
        ],
        [Input("checklist-labels-type", "value"),
         State("machine-dropdown", "value"),
         ]
    )
    def on_labels_type_change(labels_type, machine_name):
        filter_predicted_style = dict() if labels_type == 2 else dict(display='none')  # labels_type == 2 => Predicted
        manual_events_enable_untagging = data_object["configurations"]["manual_tagging"]["enable_untagging"]

        show_untag_button = labels_type == 3 and manual_events_enable_untagging
        untag_manual_event_style = {
            'font-size': '14px',
            "background-color": main_color,
            "background-image":
                f"-webkit-gradient(linear, left top, left bottom, "
                f"from({secondary_color}), to({main_color}))",
            'margin-left': "15px",
        } if show_untag_button else dict(display='none')  # labels_type == 3 => Manual

        machine_id = get_machine_id_by_name(machine_name)
        selected_machine_metadata = data_object["data_sources_metadata"][machine_id]
        selected_machine_events = get_machine_events(data_object,
                                                     labels_type,
                                                     machine_id,
                                                     False)
        data_object['selected_machine_events'] = selected_machine_events

        if not selected_machine_events.empty:
            start_date_dt, end_date_dt = update_event_id(labels_type, data_object, machine_id, 0,
                                                         selected_machine_events)

            filter_by = "no_filter" if not labels_type == 2 else "start_timestamp"
            relevant_anomalies_df = data_object['selected_event_anomalies'] \
                if labels_type == 2 and 'selected_event_anomalies' in data_object else None
            if labels_type == 1:
                data_sources_checklist = []
            else:
                if data_object['configurations']['pipeline_versions']['events_pipe_version'] == 'manual':
                    filter_by = 'no_filter'
                data_sources_checklist = get_initial_data_sources_to_show(machine_id,
                                                                          data_object,
                                                                          relevant_anomalies_df,
                                                                          filter_by=filter_by)

            metadata_div_children = create_sidebar_metadata(machine_id,
                                                            selected_machine_metadata,
                                                            selected_machine_events,
                                                            start_date_dt, end_date_dt,
                                                            "events-data",
                                                            labels_type)
            return metadata_div_children, \
                data_sources_checklist, \
                False, \
                create_plot_element_children(), \
                create_static_plot_element_children(), \
                filter_predicted_style, \
                untag_manual_event_style
        else:
            print("No manual events yet")
            selected_data_sources = []
            metadata_div_children = create_sidebar_metadata(machine_id,
                                                            selected_machine_metadata,
                                                            selected_machine_events,
                                                            None, None,
                                                            "events-data",
                                                            labels_type)

            return metadata_div_children, \
                selected_data_sources, \
                False, \
                create_plot_element_children(), \
                create_static_plot_element_children(), \
                filter_predicted_style, \
                untag_manual_event_style

    @app.callback(
        [Output('event-id-label', 'children', allow_duplicate=True),
         Output('event-type-label', 'children', allow_duplicate=True),
         Output('date-time-picker', 'startDate', allow_duplicate=True),
         Output('date-time-picker', 'endDate', allow_duplicate=True),
         Output("data-sources-checklist", 'value', allow_duplicate=True),
         Output("event-id-input", "value"),
         Output("btn-tag-timeframe", "disabled", allow_duplicate=True),
         Output(GRAPH_ID, "figure", allow_duplicate=True),
         Output(OVERVIEW_GRAPH_ID, "figure", allow_duplicate=True),
         Output(GRAPH_ID, "style", allow_duplicate=True),
         Output(OVERVIEW_GRAPH_ID, "style", allow_duplicate=True),
         Output(STORE_ID, "data", allow_duplicate=True),

         ],
        [Input('load-next-event', 'n_clicks'),
         Input('load-previous-event', 'n_clicks'),
         State('machine-dropdown', 'value'),
         State("data-sources-checklist", "value"),
         State("checkbox-show-labeled-events", "checked"),
         State("labeled-events-types-checklist", "value"),
         State("checkbox-show-pred-anomalies", "checked"),
         State("checkbox-show-pred-events", "checked"),
         State("checkbox-show-manual-events", "checked"),
         State('navigate-fast', 'checked'),
         State('checkbox-show-algo-results', 'checked'),
         State("checklist-labels-type", "value"),
         State(GRAPH_ID, "figure"),
         State(OVERVIEW_GRAPH_ID, "figure"),
         State(GRAPH_ID, "style"),
         State(OVERVIEW_GRAPH_ID, "style"),
         State(STORE_ID, "data"),
         State("checkbox-filter-pred-events", "checked"),
         State("checklist-labels-type", "value")
         ],
        prevent_initial_call=True
    )
    def load_relevant_event(next_event_n_clicks, previous_event_n_clicks,
                            machine_name, analyzed_data_sources,
                            draw_labeled_events, selected_labeled_events_types,
                            draw_predicted_anomalies, draw_predicted_events,
                            draw_manual_events,
                            navigate_fast, show_algo_results, labels_type,
                            graph_fig, overview_fig, graph_style, overview_style, stored_data,
                            is_filtering_predicted,
                            label_type):

        if next_event_n_clicks or previous_event_n_clicks:
            machine_id = get_machine_id_by_name(machine_name)
            selected_machine_metadata = data_object["data_sources_metadata"][machine_id]
            selected_machine_events = data_object['selected_machine_events']
            trigger = callback_context.triggered[0]
            pressed_button = trigger["prop_id"].split(".")[0]
            if pressed_button == "load-next-event":
                new_internal_print_id = data_object['selected_event_internal'] + 1

                start_date_dt, end_date_dt = update_event_id(labels_type,
                                                             data_object,
                                                             machine_id,
                                                             new_internal_print_id,
                                                             selected_machine_events)

            if pressed_button == "load-previous-event":
                new_internal_print_id = data_object['selected_event_internal'] - 1
                end_date_dt, start_date_dt = update_event_id(labels_type,
                                                             data_object,
                                                             machine_id,
                                                             new_internal_print_id,
                                                             selected_machine_events)

            curr_graph_fig = graph_fig
            curr_overview_fig = overview_fig
            curr_graph_style = graph_style
            curr_overview_style = overview_style
            curr_stored_data = stored_data

            start_ts = start_date_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            end_ts = end_date_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            filter_by = "no_filter" if labels_type == 3 else "start_timestamp"
            relevant_anomalies_df = data_object['selected_event_anomalies'] if labels_type == 2 else None
            if labels_type == 1:
                data_sources_checklist = analyzed_data_sources
            else:
                data_sources_checklist = get_initial_data_sources_to_show(machine_id,
                                                                          data_object,
                                                                          relevant_anomalies_df,
                                                                          filter_by=filter_by)
            if navigate_fast:
                curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data = \
                    create_graph_content(data_object,
                                         machine_name,
                                         start_ts,
                                         end_ts,
                                         data_sources_checklist,
                                         draw_labeled_events,
                                         selected_labeled_events_types,
                                         draw_predicted_anomalies,
                                         draw_predicted_events,
                                         draw_manual_events,
                                         show_algo_results)
                if curr_graph_fig is None:
                    return no_update

            return get_event_id_str(selected_machine_events), \
                get_event_type_str(selected_machine_events, data_object['selected_event_internal']), \
                start_ts, end_ts, analyzed_data_sources, data_object['selected_event_internal'] + 1, False, \
                curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data

        raise PreventUpdate("No button pressed")

    @app.callback(
        [
            Output("btn-tag-timeframe", "disabled", allow_duplicate=True),
            Output(GRAPH_ID, "figure", allow_duplicate=True),
            Output(OVERVIEW_GRAPH_ID, "figure", allow_duplicate=True),
            Output(GRAPH_ID, "style", allow_duplicate=True),
            Output(OVERVIEW_GRAPH_ID, "style", allow_duplicate=True),
            Output(STORE_ID, "data", allow_duplicate=True),
        ],
        [
            Input("show-event-data", "n_clicks"),
            State("machine-dropdown", "value"),
            State("date-time-picker", "startDate"),
            State("date-time-picker", "endDate"),
            State("data-sources-checklist", "value"),
            State("checkbox-show-labeled-events", "checked"),
            State("labeled-events-types-checklist", "value"),
            State("checkbox-show-pred-anomalies", "checked"),
            State("checkbox-show-pred-events", "checked"),
            State("checkbox-show-manual-events", "checked"),
            State("checkbox-show-algo-results", "checked")
        ],
        prevent_initial_call=True,
    )
    def update_output_events(
            show_raw_data_n_clicks,
            machine_name,
            start_timestamp,
            end_timestamp,
            analyzed_data_sources,
            draw_labeled_events,
            selected_labeled_events_types,
            draw_predicted_anomalies,
            draw_predicted_events,
            draw_manual_events,
            show_algo_results,
    ):
        if show_raw_data_n_clicks:
            curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data = \
                create_graph_content(data_object,
                                     machine_name,
                                     start_timestamp,
                                     end_timestamp,
                                     analyzed_data_sources,
                                     draw_labeled_events,
                                     selected_labeled_events_types,
                                     draw_predicted_anomalies,
                                     draw_predicted_events,
                                     draw_manual_events,
                                     show_algo_results)
            if curr_graph_fig is None:
                return no_update
            return [False, curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data]
        else:
            return no_update

    @app.callback(
        [
            Output('date-time-picker', 'startDate', allow_duplicate=True),
            Output('date-time-picker', 'endDate', allow_duplicate=True),
            Output("btn-tag-timeframe", "disabled", allow_duplicate=True),
            Output(GRAPH_ID, "figure", allow_duplicate=True),
            Output(OVERVIEW_GRAPH_ID, "figure", allow_duplicate=True),
            Output(GRAPH_ID, "style", allow_duplicate=True),
            Output(OVERVIEW_GRAPH_ID, "style", allow_duplicate=True),
            Output(STORE_ID, "data", allow_duplicate=True),

        ],
        [Input('load-next-dates', 'n_clicks'),
         Input('load-previous-dates', 'n_clicks'),
         State("date-time-picker", "startDate"),
         State("date-time-picker", "endDate"),
         State('machine-dropdown', 'value'),
         State("data-sources-checklist", "value"),
         State("checkbox-show-labeled-events", "checked"),
         State("labeled-events-types-checklist", "value"),
         State("checkbox-show-pred-anomalies", "checked"),
         State("checkbox-show-pred-events", "checked"),
         State("checkbox-show-manual-events", "checked"),
         State('navigate-dates-fast', 'checked'),
         State('checkbox-show-algo-results', 'checked'),
         State(GRAPH_ID, "figure"),
         State(OVERVIEW_GRAPH_ID, "figure"),
         State(GRAPH_ID, "style"),
         State(OVERVIEW_GRAPH_ID, "style"),
         State(STORE_ID, "data")
         ],
        prevent_initial_call=True
    )
    def load_relevant_dates(next_dates_n_clicks, previous_dates_n_clicks,
                            start_timestamp, end_timestamp,
                            machine_name, analyzed_data_sources,
                            draw_labeled_events, selected_labeled_events_types,
                            draw_predicted_anomalies, draw_predicted_events,
                            draw_manual_events,
                            navigate_fast, show_algo_results,
                            graph_fig, overview_fig, graph_style, overview_style, stored_data,
                            ):

        if next_dates_n_clicks or previous_dates_n_clicks:

            current_start_date = try_parsing_date(start_timestamp)
            current_end_date = try_parsing_date(end_timestamp)
            delta = current_end_date - current_start_date

            trigger = callback_context.triggered[0]
            pressed_button = trigger["prop_id"].split(".")[0]

            if pressed_button == "load-next-dates":
                new_start_date = current_end_date
                new_end_date = current_end_date + delta

            if pressed_button == "load-previous-dates":
                new_start_date = current_start_date - delta
                new_end_date = current_start_date

            curr_graph_fig = graph_fig
            curr_overview_fig = overview_fig
            curr_graph_style = graph_style
            curr_overview_style = overview_style
            curr_stored_data = stored_data

            new_start_ts = new_start_date.strftime("%Y-%m-%dT%H:%M:%S")
            new_end_ts = new_end_date.strftime("%Y-%m-%dT%H:%M:%S")

            if navigate_fast:
                curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data = \
                    create_graph_content(data_object,
                                         machine_name,
                                         new_start_ts,
                                         new_end_ts,
                                         analyzed_data_sources,
                                         draw_labeled_events,
                                         selected_labeled_events_types,
                                         draw_predicted_anomalies,
                                         draw_predicted_events,
                                         draw_manual_events,
                                         show_algo_results)
                if curr_graph_fig is None:
                    return no_update

            return new_start_ts, new_end_ts, False, \
                curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data

        raise PreventUpdate("No button pressed")

    @app.callback(
        [
            Output("btn-tag-timeframe", "disabled", allow_duplicate=True),
            Output(GRAPH_ID, "figure", allow_duplicate=True),
            Output(OVERVIEW_GRAPH_ID, "figure", allow_duplicate=True),
            Output(GRAPH_ID, "style", allow_duplicate=True),
            Output(OVERVIEW_GRAPH_ID, "style", allow_duplicate=True),
            Output(STORE_ID, "data", allow_duplicate=True),
        ],
        [
            Input("show-raw-data", "n_clicks"),
            State("machine-dropdown", "value"),
            State("date-time-picker", "startDate"),
            State("date-time-picker", "endDate"),
            State("data-sources-checklist", "value"),
            State("checkbox-show-labeled-events", "checked"),
            State("labeled-events-types-checklist", "value"),
            State("checkbox-show-pred-anomalies", "checked"),
            State("checkbox-show-pred-events", "checked"),
            State("checkbox-show-manual-events", "checked"),
            State("checkbox-show-algo-results", "checked")
        ],
    )
    def update_output_raw(
            show_raw_data_n_clicks,
            machine_name,
            start_timestamp,
            end_timestamp,
            analyzed_data_sources,
            draw_labeled_events,
            selected_labeled_events_types,
            draw_predicted_anomalies,
            draw_predicted_events,
            draw_manual_events,
            show_algo_results,
    ):
        if show_raw_data_n_clicks:
            curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data = \
                create_graph_content(data_object,
                                     machine_name,
                                     start_timestamp,
                                     end_timestamp,
                                     analyzed_data_sources,
                                     draw_labeled_events,
                                     selected_labeled_events_types,
                                     draw_predicted_anomalies,
                                     draw_predicted_events,
                                     draw_manual_events,
                                     show_algo_results)
            if curr_graph_fig is None:
                return no_update
            return [False, curr_graph_fig, curr_overview_fig, curr_graph_style, curr_overview_style, curr_stored_data]
        else:
            return no_update

    @app.callback(
        Output("download-dialog", "data"),
        [Input("btn-download", "n_clicks")],
        [
            State(GRAPH_ID, "figure"),
            State("machine-dropdown", "value"),
            State("date-time-picker", "startDate"),
            State("date-time-picker", "endDate"),
        ],
        prevent_initial_call=True,
    )
    def save_to_html(n_clicks, fig, machine_name, start_timestamp, end_timestamp):
        machine_id = get_machine_id_by_name(machine_name)
        start_date_str = try_parsing_date(start_timestamp).strftime("%Y-%m-%d_%H-%M-%S")
        end_date_str = try_parsing_date(end_timestamp).strftime("%Y-%m-%d_%H-%M-%S")

        if n_clicks is not None:
            filename = f"{machine_id}__{start_date_str}_{end_date_str}_exploration.html"
            figure = go.Figure(fig)
            return dict(content=figure.to_html(), filename=filename)

    @app.callback(
        Output("btn-tag-timeframe", "n_clicks"),
        [Input("btn-tag-timeframe", "n_clicks")],
        [
            State(GRAPH_ID, "figure"),
            State("machine-dropdown", "value"),
            State("data-sources-checklist", "value"),

        ],
        prevent_initial_call=True,
    )
    def add_manual_event_to_saved(n_clicks, fig, machine_name, analyzed_data_sources):
        if n_clicks is not None:
            data_source_ids = [
                int(get_data_source_id_by_name(data_source_name))
                for data_source_name in analyzed_data_sources
            ]
            machine_id = get_machine_id_by_name(machine_name)

            add_manual_event_function = add_manual_event_to_db \
                if data_object['configurations']['manual_tagging']['use_db'] else add_manual_event_to_csv

            pipelines_configurations = {key: value.item() if isinstance(value, numpy.integer) else value for key, value
                                        in
                                        data_object['configurations']['pipeline_versions'].items()}

            add_manual_event_function(machine_id=machine_id,
                                      data_source_ids=data_source_ids,
                                      start_timestamp=try_parsing_date(fig['layout']['xaxis']['range'][0]),
                                      end_timestamp=try_parsing_date(fig['layout']['xaxis']['range'][1]),
                                      username=data_object['configurations']['manual_tagging']['username'],
                                      insert_timestamp=datetime.now(),
                                      pipelines_configurations=json.dumps(pipelines_configurations))

            reading_manual_events_function = load_manual_events_from_db \
                if data_object['configurations']['manual_tagging']['use_db'] else load_manual_events_from_csv

            data_object["events"]['manual'] = reading_manual_events_function(
                before_hours=data_object["configurations"]["time_configurations"]["show_before_event"],
                after_hours=data_object["configurations"]["time_configurations"]["show_after_event"],
                load_deprecated=data_object["configurations"]["manual_tagging"]["show_deprecated"])

            return n_clicks
        return no_update

    @app.callback(
        [Output('date-time-picker', 'startDate', allow_duplicate=True),
         Output('date-time-picker', 'endDate', allow_duplicate=True),
         Output("data-sources-checklist", 'value', allow_duplicate=True),
         Output('event-id-label', 'children', allow_duplicate=True),
         Output('event-type-label', 'children', allow_duplicate=True)],
        [Input("btn-untag-timeframe", "n_clicks")],
        [
            State("checklist-labels-type", "value"),
        ],
        prevent_initial_call=True,
    )
    def remove_manual_event_from_saved(n_clicks, labels_type):
        if n_clicks is not None:
            if labels_type != 3:
                # TODO: Create pop up
                print("Deleting manual events is possible only from Manual Events configuration")
                return no_update

            event_id, _, machine_id, data_source_ids, start_timestamp, end_timestamp, username, _, _, _, _, _, _, _, = \
                data_object['selected_machine_events'].iloc[data_object['selected_event_internal']]

            remove_manual_event_function = remove_manual_event_from_db \
                if data_object['configurations']['manual_tagging']['use_db'] else remove_manual_event_from_csv

            remove_manual_event_function(machine_id=machine_id,
                                         start_timestamp=start_timestamp,
                                         end_timestamp=end_timestamp,
                                         username=username,
                                         event_id=event_id)

            reading_manual_events_function = load_manual_events_from_db \
                if data_object['configurations']['manual_tagging']['use_db'] else load_manual_events_from_csv

            data_object["events"]['manual'] = reading_manual_events_function(
                before_hours=data_object["configurations"]["time_configurations"]["show_before_event"],
                after_hours=data_object["configurations"]["time_configurations"]["show_after_event"],
                load_deprecated=data_object["configurations"]["manual_tagging"]["show_deprecated"])

            selected_machine_events = get_machine_events(data_object, labels_type, machine_id, False)
            data_object['selected_machine_events'] = selected_machine_events

            start_date_dt, end_date_dt = update_event_id(labels_type,
                                                         data_object,
                                                         machine_id,
                                                         data_object['internal_event_id'],
                                                         selected_machine_events)
            data_sources_checklist = get_initial_data_sources_to_show(machine_id,
                                                                      data_object,
                                                                      None,
                                                                      filter_by="no_filter")

            data_source_description = get_event_type_str(selected_machine_events,
                                                         data_object['selected_event_internal'])
            event_id_label = get_event_id_str(selected_machine_events)

            return start_date_dt, end_date_dt, data_sources_checklist, event_id_label, data_source_description
        return no_update

    # --- off canvas update logic ---
    @app.callback(
        Output("offcanvas-data-sources-metadata", "is_open"),
        Input("open-offcanvas-data-sources-metadata", "n_clicks"),
        [State("offcanvas-data-sources-metadata", "is_open")],
    )
    def toggle_offcanvas_metadata(n1, is_open):
        if n1:
            return not is_open
        return is_open

    @app.callback(
        Output("offcanvas-machines-metadata", "is_open"),
        Input("open-offcanvas-machines-metadata", "n_clicks"),
        [State("offcanvas-machines-metadata", "is_open")],
    )
    def toggle_offcanvas_machines_metadata(n1, is_open):
        if n1:
            return not is_open
        return is_open

    # --- FigureResampler update logic ---
    @app.callback(
        Output(TRACEUPDATER_ID, "updateData"),
        Input(GRAPH_ID, "relayoutData"),
        State(STORE_ID, "data"),  # The server side cached FigureResampler per session
        prevent_initial_call=True,
    )
    def update_fig(relayoutdata, fig):
        if fig is None:
            return no_update
        return fig.construct_update_data(relayoutdata)

    # --- Clientside callbacks used to bidirectionally link the overview and main graph ---
    app.clientside_callback(
        dash.ClientsideFunction(namespace="clientside", function_name="main_to_coarse"),
        dash.Output(OVERVIEW_GRAPH_ID, "id", allow_duplicate=True),  # TODO -> look for clean output
        dash.Input(GRAPH_ID, "relayoutData"),
        [dash.State(OVERVIEW_GRAPH_ID, "id"),
         dash.State(GRAPH_ID, "id")],
        prevent_initial_call=True,
    )

    app.clientside_callback(
        dash.ClientsideFunction(namespace="clientside", function_name="coarse_to_main"),
        dash.Output(GRAPH_ID, "id", allow_duplicate=True),
        dash.Input(OVERVIEW_GRAPH_ID, "selectedData"),
        [dash.State(GRAPH_ID, "id"),
         dash.State(OVERVIEW_GRAPH_ID, "id")],
        prevent_initial_call=True,
    )
