import uuid

from dash import dcc, html
import dash_bootstrap_components as dbc

import dash_mantine_components as dmc

from src.keter_globals import *
from src.widgets.widgets_utils import CustomButton, create_upload_component


def create_calculated_labels_pipeline_children(labeled_events_pipe_options, labeled_events_pipe_version):
    widget_children = [
        dbc.Label("Labeled Events Pipeline (2.5) Version:"),
        dcc.Dropdown(labeled_events_pipe_options,
                     labeled_events_pipe_version,
                     id="labeled-events-pipe-version-label")
    ]
    if labeled_events_pipe_version == 'manual':
        # TODO: Change 'max_files=5' to number of machines
        widget_children.append(create_upload_component('upload-labeled-events-files', 'labeled events', max_files=5))
        widget_children.append(html.Div(id='callback-output', children=[]))
    return widget_children


def create_training_pipeline_children(training_pipe_options, training_pipe_version):
    widget_children = [
        dbc.Label("Training Pipeline (3) Version:"),
        dcc.Dropdown(training_pipe_options,
                     training_pipe_version,
                     id="training-pipe-version-label")]
    if training_pipe_version == 'manual':
        widget_children.append(create_upload_component('upload-reconstruction-files', 'reconstruction', 10))

    return widget_children


def create_predicted_events_pipeline_children(events_pipe_options, events_pipe_version):
    widget_children = [
        dbc.Label("Predicted Events Pipeline (5) Version:"),
        dcc.Dropdown(events_pipe_options,
                     events_pipe_version,
                     id="pred-events-pipe-version-label"),
    ]

    if events_pipe_version == 'manual':
        widget_children += [
            # TODO: Change 'max_files=5' to number of machines
            create_upload_component('upload-anomalies-files', 'predicted anomalies', max_files=5),
            create_upload_component('upload-events-files', 'predicted events', max_files=5)
        ]
    return widget_children


def create_pipeline_versions_widget(pipeline_versions, pipeline_selected_versions):
    versions_children = [
        dbc.Label("Pipelines Versions", style={'color': main_color, 'font-size': '20px'}),
        html.Br(),
        CustomButton("Refresh versions", id="refresh-pipeline-versions-button", n_clicks=0),
        html.Br(),
        html.Div(children=[dbc.Label("Statistics Pipeline (2) Version:"),
                           dcc.Dropdown(pipeline_versions['stats_pipe_options'],
                                        pipeline_selected_versions['stats_pipe_version'],
                                        id="stats-pipe-version-label"),
                           html.Br(),
                           html.Div(id='labeled-events-config-div',
                                    children=create_calculated_labels_pipeline_children(
                                        pipeline_versions['labeled_events_pipe_options'],
                                        pipeline_selected_versions['labeled_events_pipe_version'])),

                           html.Br(),
                           html.Div(id='training-config-div',
                                    children=create_training_pipeline_children(
                                        pipeline_versions['training_pipe_options'],
                                        pipeline_selected_versions['training_pipe_version'])),

                           html.Br(),
                           html.Div(id='predicted-events-config-div',
                                    children=create_predicted_events_pipeline_children(
                                        pipeline_versions['events_pipe_options'],
                                        pipeline_selected_versions['events_pipe_version']))

                           ], className='divBorder')]

    return versions_children


def create_configurations_form(pipeline_versions, pipeline_selected_versions):
    versions_widget_children = create_pipeline_versions_widget(pipeline_versions, pipeline_selected_versions)
    versions_button = dbc.Button("Select Configurations", id="open-configurations-modal", n_clicks=0,
                                 style={
                                     'font-size': '12px',
                                     "background-color": main_color,
                                     "background-image": f"-webkit-gradient(linear, left top, "
                                                         f"left bottom, from({secondary_color}), to({main_color}))"},
                                 )
    versions_form = dbc.Modal(
        [
            dbc.ModalHeader([dbc.ModalTitle("Configurations", style={'color': main_color})]),
            dbc.ModalBody(
                versions_widget_children +
                [
                    html.Br(),
                    dbc.Label("Events Configurations", style={'color': main_color, 'font-size': '20px'}),
                    html.Br(),
                    html.Div(children=[
                        dbc.Label("Maximum data sources per event: "),
                        dbc.Input(id='max-data-sources-event-label',
                                  type="number",
                                  min=5, max=100, step=1, value=15,
                                  style={'display': "inline-block", 'width': "4rem", "margin-left": "31px"}),
                        dbc.Label("Hours to show before an event: "),
                        dbc.Input(id='hours-before-event-label',
                                  type="number",
                                  min=0.5, max=5, step=0.5, value=3,
                                  style={'display': "inline-block", 'width': "4rem", "margin-left": "48px"}),
                        dbc.Label("Hours to show after an event:"),
                        dbc.Input(id='hours-after-event-label',
                                  type="number",
                                  min=0.5, max=3, step=0.5, value=1,
                                  style={'display': "inline-block", 'width': "4rem", "margin-left": "62px"}),
                        # html.Br(),
                        # dbc.Label("Order data sources in events by:"),
                        # dcc.Dropdown(['start_timestamp', 'num_anomalies', 'no_filter'],
                        #              value='start_timestamp',
                        #              id="order-data-sources-in-events-label",
                        #              disabled=True),
                    ], className='divBorder'),
                    html.Br(),
                    dbc.Label("Manual Events Configurations", style={'color': main_color, 'font-size': '20px'}),
                    html.Br(),
                    html.Div(children=[
                        dbc.Label("Username:"),
                        dcc.Dropdown(options=['Unknown'] + sorted(possible_users), value='Unknown', id="manual-tagging-username-label"),
                        html.Br(),
                        dmc.Checkbox(
                            id="write-to-db-checkbox",
                            label="Use Database",
                            mb=10,
                            checked=True,
                            color='blue'
                        ),
                        dmc.Checkbox(
                            id="show-deprecated-manual-events-checkbox",
                            label="Show Deprecated Events",
                            mb=10,
                            checked=False,
                            color='blue'
                        ),
                        dmc.Checkbox(
                            id="enable-untagging-checkbox",
                            label="Enable Untagging Events",
                            mb=10,
                            checked=False,
                            disabled=True,
                            color='red'
                        ),
                    ], className='divBorder'),
                    dbc.Label("Note: If you press OK, the dashboard and cache will reset", color=main_color),
                ]
            ),
            dbc.ModalFooter(
                [
                    dcc.Loading(
                        html.Div([
                            CustomButton("OK", id="versions-modal-ok-button", n_clicks=0),
                            CustomButton("Cancel", id="versions-modal-cancel-button", n_clicks=0)
                        ]),
                        type='dot',
                        color='crimson',
                        style={"margin-top": "50rem"}
                    )
                ]
            ),
        ],
        id="pipelines-versions-modal",
        is_open=True
    )
    return versions_button, versions_form
