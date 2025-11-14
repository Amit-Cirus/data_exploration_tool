import os
import shutil
from typing import Tuple

from dash import Input, Output, State, no_update, callback_context, html

from src.widgets.configuration_widget_creation import (
    create_calculated_labels_pipeline_children,
    create_training_pipeline_children,
    create_predicted_events_pipeline_children
)

from src.widgets.tabs_creation_utils import create_tabs_children

from src.data_loaders.algo.keter_algorithmic_reconstruction_data import parse_manual_reconstruction_contents
from src.data_loaders.keter_labeled_events import parse_manual_labeled_events_contents
from src.data_loaders.keter_raw_data import get_machine_names
from src.data_loaders.keter_data_loader import (
    initialize_data_object,
    update_config
)
from src.data_loaders.keter_pipelines_versions_loader import (
    get_events_pipe_options,
    get_training_pipe_options
)
from src.data_loaders.algo.keter_algorithmic_events_data import (
    parse_manual_predicted_anomalies_contents,
    parse_manual_predicted_events_contents
)


def create_configurations_callbacks(app, data_object):
    @app.callback(
        [Output("pipelines-versions-modal", "is_open", allow_duplicate=True),
         Output("stats-pipe-version-label", "value", allow_duplicate=True),
         Output("labeled-events-pipe-version-label", "value", allow_duplicate=True),
         Output("training-pipe-version-label", "value", allow_duplicate=True),
         Output("pred-events-pipe-version-label", "value", allow_duplicate=True),
         Output("max-data-sources-event-label", "value"),
         Output("hours-before-event-label", "value"),
         Output("hours-after-event-label", "value"),
         Output("manual-tagging-username-label", "value"),
         Output("write-to-db-checkbox", "checked"),
         Output("show-deprecated-manual-events-checkbox", "checked"),
         Output("enable-untagging-checkbox", "checked")],
        [Input("open-configurations-modal", "n_clicks")],
        prevent_initial_call=True
    )
    def show_versions_modal(n_open_modal: int) -> Tuple[bool, str, str, str, str, int, float, float, str, bool, bool, bool]:
        if n_open_modal > 0:
            manual_tagging = data_object["configurations"]["manual_tagging"]
            pipeline_versions = data_object["configurations"]["pipeline_versions"]
            time_configurations = data_object["configurations"]["time_configurations"]
            events_configurations = data_object["configurations"]["events_configurations"]
            return (
                True,
                pipeline_versions["stats_pipe_version"],
                pipeline_versions["labeled_events_pipe_version"],
                pipeline_versions["training_pipe_version"],
                pipeline_versions["events_pipe_version"],
                events_configurations["max_data_sources_to_show"],
                time_configurations["show_before_event"],
                time_configurations["show_after_event"],
                manual_tagging["username"],
                manual_tagging["use_db"],
                manual_tagging["show_deprecated"],
                manual_tagging["enable_untagging"])
        return no_update

    @app.callback(
        [Output("pipelines-versions-modal", "is_open", allow_duplicate=True)],
        [Input("versions-modal-cancel-button", "n_clicks")],
        prevent_initial_call=True
    )
    def close_modal(n_cancel_modal: int) -> bool:
        trigger = callback_context.triggered[0]
        pressed_button = trigger["prop_id"].split(".")[0]
        if pressed_button == "versions-modal-cancel-button":
            return False
        return no_update

    @app.callback(
        [Output("enable-untagging-checkbox", "disabled", allow_duplicate=True),
         Output("enable-untagging-checkbox", "checked", allow_duplicate=True)],
        [Input("manual-tagging-username-label", "value")],
        [State("enable-untagging-checkbox", "checked")],
        prevent_initial_call=True
    )
    def enable_untagging_checkbox(manual_tagging_username: str, enable_untagging) -> Tuple[bool, bool]:
        if manual_tagging_username == 'Eri':
            return False, enable_untagging
        else:
            return True, False

    @app.callback(
        [
            Output('tabs', 'children'),
            Output("pipelines-versions-modal", "is_open", allow_duplicate=True)
        ],
        [Input("versions-modal-ok-button", "n_clicks"),
         Input("versions-modal-cancel-button", "n_clicks")],
        [State("stats-pipe-version-label", "value"),
         State("labeled-events-pipe-version-label", "value"),
         State("training-pipe-version-label", "value"),
         State("pred-events-pipe-version-label", "value"),
         State("max-data-sources-event-label", "value"),
         State("hours-before-event-label", "value"),
         State("hours-after-event-label", "value"),
         State("manual-tagging-username-label", "value"),
         State("write-to-db-checkbox", "checked"),
         State("show-deprecated-manual-events-checkbox", "checked"),
         State("enable-untagging-checkbox", "checked")
         ],
        prevent_initial_call=True
    )
    def update_versions(n_ok_modal: int, n_cancel_modal: int,
                        stats_pipe_version: str, labeled_events_pipe_version: str,
                        train_pipe_version: str, pred_events_pipe_version: str,
                        max_data_sources_per_event: int,
                        hours_before_event: str, hours_after_event: str, username: str,
                        manual_events_use_db: bool,
                        manual_events_show_deprecated: bool,
                        manual_events_enable_untagging: bool) -> Tuple[list, bool]:
        trigger = callback_context.triggered[0]
        pressed_button = trigger["prop_id"].split(".")[0]
        if pressed_button == "versions-modal-ok-button":
            pipeline_versions = data_object["configurations"]["pipeline_versions"]
            pipeline_versions["stats_pipe_version"] = stats_pipe_version
            pipeline_versions["labeled_events_pipe_version"] = labeled_events_pipe_version
            pipeline_versions["training_pipe_version"] = train_pipe_version
            pipeline_versions["events_pipe_version"] = pred_events_pipe_version

            events_configurations = data_object["configurations"]["events_configurations"]
            events_configurations["max_data_sources_to_show"] = int(max_data_sources_per_event)

            time_configurations = data_object["configurations"]["time_configurations"]
            time_configurations["show_before_event"] = float(hours_before_event)
            time_configurations["show_after_event"] = float(hours_after_event)

            manual_tagging = data_object["configurations"]["manual_tagging"]
            manual_tagging["username"] = username
            manual_tagging["use_db"] = manual_events_use_db
            manual_tagging["show_deprecated"] = manual_events_show_deprecated
            manual_tagging["enable_untagging"] = manual_events_enable_untagging

            machines_list = get_machine_names(data_object["machines"])

            # TODO: verify validity of data
            shutil.rmtree("file_system_backend")
            os.mkdir("file_system_backend")
            initialize_data_object(data_object, machines_list, only_manual_mode=False)
            return create_tabs_children(), False
        if pressed_button == "versions-modal-cancel-button":
            return no_update

        return no_update

    @app.callback(
        [Output("pred-events-pipe-version-label", "options", allow_duplicate=True),
         Output("pred-events-pipe-version-label", "value", allow_duplicate=True)
         ],
        [Input("training-pipe-version-label", "value")],
        prevent_initial_call=True
    )
    def show_versions_modal(training_version: int) -> Tuple[list, str]:
        events_pipe_versions = get_events_pipe_options(training_version)
        data_object["configurations"]["pipeline_versions_options"][
            "events_pipe_options"] = events_pipe_versions
        data_object["configurations"]["pipeline_versions"]["events_pipe_version"] = events_pipe_versions[0]
        return events_pipe_versions, events_pipe_versions[0]

    @app.callback(
        [Output("labeled-events-config-div", "children", allow_duplicate=True),
         Output("training-pipe-version-label", "options", allow_duplicate=True),
         Output("training-pipe-version-label", "value", allow_duplicate=True)
         ],
        [Input("labeled-events-pipe-version-label", "value")],
        prevent_initial_call=True
    )
    def update_labeled_event_config_widget(labeled_events_version_pipe_value):
        curr_labeled_events_pipe_version = data_object["configurations"]['pipeline_versions']['labeled_events_pipe_version']
        if curr_labeled_events_pipe_version != labeled_events_version_pipe_value:
            data_object["configurations"]['pipeline_versions']['labeled_events_pipe_version'] = labeled_events_version_pipe_value

            stats_pipe_version = data_object["configurations"]['pipeline_versions']['stats_pipe_version']
            training_hash_versions = get_training_pipe_options(stats_pipe_version, labeled_events_version_pipe_value)
            data_object["configurations"]['pipeline_versions_options']['training_pipe_options'] = training_hash_versions
            labeled_events_pipe_options = data_object['configurations']['pipeline_versions_options'][
                'labeled_events_pipe_options']
            return create_calculated_labels_pipeline_children(labeled_events_pipe_options,
                                                              labeled_events_version_pipe_value), \
                training_hash_versions, training_hash_versions[0]
        return no_update

    @app.callback(
        [
            Output("training-pipe-version-label", "options", allow_duplicate=True),
            Output("training-pipe-version-label", "value", allow_duplicate=True)
        ],
        [Input("stats-pipe-version-label", "value")],
        prevent_initial_call=True
    )
    def update_labeled_event_config_widget(stats_pipe_version):
        curr_stats_pipe_version = data_object["configurations"]['pipeline_versions']['stats_pipe_version']
        if curr_stats_pipe_version != stats_pipe_version:
            data_object["configurations"]['pipeline_versions']['stats_pipe_version'] = stats_pipe_version

            labeled_events_version_pipe_value = data_object["configurations"]['pipeline_versions']['labeled_events_pipe_version']
            training_hash_versions = get_training_pipe_options(stats_pipe_version, labeled_events_version_pipe_value)
            data_object["configurations"]['pipeline_versions_options']['training_pipe_options'] = training_hash_versions
            return training_hash_versions, training_hash_versions[0]
        return no_update

    @app.callback(
        [Output("training-config-div", "children")],
        [Input("training-pipe-version-label", "value")],
        prevent_initial_call=True
    )
    def update_training_config_widget(training_version_pipe_value):
        curr_training_version_pipe_value = data_object["configurations"]['pipeline_versions']['training_pipe_version']
        if curr_training_version_pipe_value != training_version_pipe_value:
            data_object["configurations"]['pipeline_versions']['training_pipe_version'] = training_version_pipe_value
            return create_training_pipeline_children(
                data_object['configurations']['pipeline_versions_options']['training_pipe_options'],
                training_version_pipe_value)
        return no_update

    @app.callback(
        [Output("predicted-events-config-div", "children")],
        [Input("pred-events-pipe-version-label", "value")],
        prevent_initial_call=True
    )
    def update_predicted_events_config_widget(predicted_events_version_pipe_value):
        data_object["configurations"]['pipeline_versions']['events_pipe_version'] = predicted_events_version_pipe_value
        return create_predicted_events_pipeline_children(
            data_object['configurations']['pipeline_versions_options']['events_pipe_options'],
            predicted_events_version_pipe_value)

    @app.callback(
        [Output('upload-labeled-events-files', 'children')],
        [Input('upload-labeled-events-files', 'contents')],
        [State('upload-labeled-events-files', 'filename')],
        prevent_initial_call=True
    )
    def upload_labeled_events(contents, file_names):
        if contents is not None:
            machines = list(data_object['machines'].keys())
            before_hours_config = data_object["configurations"]["time_configurations"]["show_before_event"]
            after_hours_config = data_object["configurations"]["time_configurations"]["show_after_event"]
            labeled_events_dict, machines_with_data = parse_manual_labeled_events_contents(
                contents,
                file_names,
                machines=machines,
                before_hours=before_hours_config,
                after_hours=after_hours_config)
            data_object["events"]['labeled'] = labeled_events_dict
            children = html.Div([f"Files were uploaded for machines {','.join(machines_with_data)}"]),
            return children
        return no_update

    @app.callback(
        [Output('upload-anomalies-files', 'children')],
        [Input('upload-anomalies-files', 'contents')],
        [State('upload-anomalies-files', 'filename')],
        prevent_initial_call=True
    )
    def upload_predicted_anomalies(contents, file_names):
        if contents is not None:
            _, machines_with_data = parse_manual_predicted_anomalies_contents(contents, file_names)
            if len(machines_with_data) == 1:
                shown_str = f"Files were uploaded for machine {','.join(machines_with_data)}"
            elif len(machines_with_data) > 1:
                shown_str = f"Files were uploaded for machines {','.join(machines_with_data)}"
            else:
                shown_str = "No files were uploaded"
            children = html.Div([shown_str])
            return children

        return no_update

    @app.callback(
        [Output('upload-events-files', 'children')],
        [Input('upload-events-files', 'contents')],
        [State('upload-events-files', 'filename')],
        prevent_initial_call=True
    )
    def upload_predicted_events(contents, file_names):
        if contents is not None:
            before_hours_config = data_object["configurations"]["time_configurations"]["show_before_event"]
            after_hours_config = data_object["configurations"]["time_configurations"]["show_after_event"]
            predicted_events_dict, machines_with_data = parse_manual_predicted_events_contents(
                contents, file_names,
                before_hours=before_hours_config,
                after_hours=after_hours_config
            )
            data_object['algo']['predicted_events'] = predicted_events_dict
            if len(machines_with_data) == 1:
                shown_str = f"Files were uploaded for machine {','.join(machines_with_data)}"
            elif len(machines_with_data) > 1:
                shown_str = f"Files were uploaded for machines {','.join(machines_with_data)}"
            else:
                shown_str = "No files were uploaded"
            children = html.Div([shown_str])

            return children

        return no_update

    @app.callback(
        [Output('upload-reconstruction-files', 'children')],
        [Input('upload-reconstruction-files', 'contents')],
        [State('upload-reconstruction-files', 'filename')],
        prevent_initial_call=True
    )
    def upload_reconstruction_events(contents, file_names):
        if contents is not None:
            reconstruction_dict, data_sources_with_data = parse_manual_reconstruction_contents(contents, file_names)
            data_object["algo"]['reconstruction'] = reconstruction_dict
            if len(data_sources_with_data) == 1:
                shown_str = f"Reconstruction files were uploaded for {','.join(data_sources_with_data)}"
            elif len(data_sources_with_data) > 1:
                shown_str = f"Reconstruction files were uploaded for {','.join(data_sources_with_data)}"
            else:
                shown_str = "No files were uploaded"
            children = html.Div([shown_str])
            return children

        return no_update

    @app.callback(
        [Output("stats-pipe-version-label", "value", allow_duplicate=True),
         Output("labeled-events-pipe-version-label", "value", allow_duplicate=True),
         Output("training-pipe-version-label", "value", allow_duplicate=True),
         Output("pred-events-pipe-version-label", "value", allow_duplicate=True)],
        [Input('refresh-pipeline-versions-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def refresh_versions(refresh_nclicks):
        trigger = callback_context.triggered[0]
        pressed_button = trigger["prop_id"].split(".")[0]
        if pressed_button == "refresh-pipeline-versions-button":
            try:
                manual_predicted_filename = os.path.join("temporary_data", "anomalies_manual.csv")
                os.remove(manual_predicted_filename)
            except OSError:
                pass
            update_config(data_object)
            pipeline_versions = data_object["configurations"]["pipeline_versions"]
            return (pipeline_versions["stats_pipe_version"],
                    pipeline_versions["labeled_events_pipe_version"],
                    pipeline_versions["training_pipe_version"],
                    pipeline_versions["events_pipe_version"])
        return no_update
