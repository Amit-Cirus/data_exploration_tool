from dash import dcc, html
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeSwitchAIO
import dash_mantine_components as dmc
import dash_datetimepicker
from dash import dash_table
from trace_updater import TraceUpdater

from src.data_loaders.keter_data_loader import (
    get_event_id_str,
    get_event_type_str
)

from src.data_loaders.keter_raw_data import (
    get_data_sources_by_machine,
    get_data_sources_names,
    get_machines_metadata_from_db, get_machines_metadata_from_csv
)
from src.widgets.configuration_widget_creation import create_configurations_form

from src.widgets.widgets_utils import CustomButton

from src.keter_globals import *
from assets.styles import *


def create_mode_switch_button():
    return ThemeSwitchAIO(aio_id="theme", themes=[dbc.themes.COSMO, dbc.themes.CYBORG])


def create_load_data_widget():
    return html.Div(
        [
            CustomButton("Load by Dates", id="load-raw-data", n_clicks=0),
        ]
    )


def create_full_load_data_widget_children():
    return [
        CustomButton('Load by Events', id='load-events-data',
                     n_clicks=0,
                     color="primary",
                     className="me-1"),
        CustomButton('Load by Dates', id='load-raw-data',
                     n_clicks=0,
                     style={
                         'font-size': '14px',
                         "margin-left": "15px",
                         "background-color": main_color,
                         "background-image":
                             f"-webkit-gradient(linear, left top, left bottom, "
                             f"from({main_color}), to({secondary_color}))",
                     },
                     color="primary",
                     className="me-1"),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Loading process")),
                dbc.ModalBody(id='modal-number-prints-txt', children=[]),
                dbc.ModalFooter(),
            ],
            id="modal-number-prints",
            centered=True,
            is_open=False,
        ),
    ]


def create_full_load_data_widget():
    return html.Div(
        id='load-data-widget',
        children=[
            CustomButton('Load by Events', id='load-events-data',
                         n_clicks=0,
                         color="primary",
                         className="me-1"),
            CustomButton('Load by Dates', id='load-raw-data',
                         n_clicks=0,
                         style={
                             'font-size': '14px',
                             "margin-left": "15px",
                             "background-color": main_color,
                             "background-image":
                                 f"-webkit-gradient(linear, left top, left bottom, "
                                 f"from({main_color}), to({secondary_color}))",
                         },
                         color="primary",
                         className="me-1"),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Loading process")),
                    dbc.ModalBody(id='modal-number-prints-txt', children=[]),
                    dbc.ModalFooter(),
                ],
                id="modal-number-prints",
                centered=True,
                is_open=False,
            ),
        ]
    )


def create_download_widget():
    tagging_btn = create_tagging_button()
    untagging_btn = create_untagging_button()
    return html.Div(
        [
            CustomButton(
                "Download graph", id="btn-download", color="primary", className="me-1"
            ),
            dcc.Download(id="download-dialog"),
            tagging_btn,
            untagging_btn
        ]
    )


def create_header(customer_name):
    img_asset = r"assets/idea.png"
    if customer_name == "Admatec":
        img_asset = r"assets/admatec-better-display-solution-logo-simple.png"
    if customer_name == "DragonFly":
        img_asset = r"assets/NNDM-52004d48.png"
    if customer_name == "Keter":
        img_asset = r"assets/1200px-Keter_Plastics_logo.svg.png"

    return html.Div(children=[html.Img(src=img_asset),  # create_mode_switch_button(),
                              ],
                    style=HEADER_STYLE)


def create_plot_element_children():
    return [
        dcc.Graph(id=GRAPH_ID, style={'display': 'none'}),
        dcc.Store(id=STORE_ID),
        TraceUpdater(id=TRACEUPDATER_ID, gdID=GRAPH_ID)
    ]


def create_static_plot_element_children():
    return [
        dcc.Graph(id=OVERVIEW_GRAPH_ID, style={'display': 'none'})
    ]


def create_data_sources_analysis_tab_content():
    content = dcc.Loading(
        html.Div([
            html.Div(
                [
                    html.Div(id="plot-element-static",
                             children=create_static_plot_element_children(),
                             style=STATIC_CONTENT_STYLE
                             ),
                ]),
            html.Br(),
            html.Br(),
            html.Div(html.Div(id="plot-element",
                              children=create_plot_element_children(),
                              style=CONTENT_STYLE)),
        ]),
        type='dot',
        color='crimson',
        style={"margin-top": "50rem"}
    )
    return content


def create_initial_side_bar(machines, selected_machine, pipeline_versions_options, pipeline_selected_versions, only_manual_mode):
    sidebar_children_elements = create_sidebar_children(machines, selected_machine,
                                                        pipeline_versions_options, pipeline_selected_versions,
                                                        only_manual_mode)
    return html.Div(
        id="sidebar-filter",
        style=SIDEBAR_STYLE,
        children=sidebar_children_elements
    )


def create_metadata_filters_widget(machine_id, selected_machine_df):
    selected_machine_metadata = selected_machine_df
    data_sources_dict = get_data_sources_by_machine(machine_id)
    offcanvas_metadata = create_off_canvas_data_sources_metadata(selected_machine_metadata)
    data_sources_names = get_data_sources_names(data_sources_dict)
    labeled_events_types = [event_name for event_name in list(machine_timeslot_data_groups_color_mapping.keys())
                            if event_name != 'Good']
    selected_labeled_events_types = [event_name for event_name in list(machine_timeslot_data_groups_color_mapping.keys())
                            if event_name not in ['Good', 'Pre event', 'Defective parts']]

    metadata_div_children = [
        dbc.Label("Show Data Sources Metadata", size=12, color=main_color),
        html.Br(),
        offcanvas_metadata,
        dbc.Label("Data Sources", size=12, color=main_color),
        html.Br(),
        dcc.Dropdown(
            id="data-sources-checklist",
            options=data_sources_names,
            value=[],
            multi=True,
            style={'textAlign': 'left',
                   'font-size': '14px'}
        ),
        dbc.Label("Labels", size=12, color=main_color),
        html.Br(),
        dmc.Checkbox(
            id="checkbox-show-labeled-events",
            label="Show labeled events",
            mb=10,
            color="red",
            checked=False,
        ),
        dcc.Dropdown(
            id="labeled-events-types-checklist",
            options=labeled_events_types,
            value=selected_labeled_events_types,
            multi=True,
            style={'textAlign': 'left',
                   'font-size': '14px'}
        ),
        dbc.Tooltip(
            machine_timeslot_data_groups_color_mapping_tooltip,
            id="labeled-events-types-color-tooltip",
            target="labeled-events-types-checklist",
            placement='right',
            style={
                'white-space': 'pre',
                  }
        ),
        html.Br(),
        dmc.Checkbox(
            id="checkbox-show-manual-events",
            label="Show manual labeled events",
            mb=10,
            color="blue",
            checked=False,
        ),
        dbc.Label("AI Results", size=12, color=main_color),
        dmc.Checkbox(
            id="checkbox-show-algo-results",
            label="Show AI reconstruction",
            mb=10,
            color="green",
            checked=False,
        ),
        dmc.Checkbox(
            id="checkbox-show-pred-anomalies",
            label="Show AI predicted anomalies",
            mb=10,
            color="orange",
            checked=False,
        ),
        dmc.Checkbox(
            id="checkbox-show-pred-events",
            label="Show AI predicted events",
            mb=10,
            color="orange",
            checked=False,
        )
    ]

    return metadata_div_children


def create_events_navigation_widget(machine_events, event_id, event_type):
    event_id_str = get_event_id_str(machine_events)
    return html.Div(
        [
            html.Br(),
            dmc.Checkbox(
                id="checkbox-filter-pred-events",
                label="Filter AI predicted events by labeled events",
                mb=10,
                color="orange",
                style=dict(display='none'),
                checked=False,
            ),
            dmc.Checkbox(
                id="navigate-fast",
                label="Navigate between events with arrows",
                mb=10,
                disabled=False,
                checked=False,

            ),
            html.Br(),
            dbc.Input(id='event-id-input',
                      type="number",
                      min=1, max=len(machine_events), step=1, value=event_id, debounce=True,
                      style={'display': "inline-block", 'width': "5rem"}),

            dbc.Label(event_id_str, id='event-id-label', size=10, color=main_color,
                      style={"margin-left": "10px"}),

            dbc.Label(event_type, id='event-type-label', size=10, style={"margin-left": "15px"}),
            html.Br(),
            html.Br(),
            CustomButton('Show Data', id='show-event-data', n_clicks=0, color="primary", className="me-1"),
            CustomButton('<<', id='load-previous-event', n_clicks=0,
                         style={
                             'font-size': '14px',
                             "margin-left": "15px",
                             "background-color": main_color,
                             "background-image":
                                 f"-webkit-gradient(linear, left top, left bottom, "
                                 f"from({main_color}), to({secondary_color}))",
                         }, ),
            CustomButton('>>', id='load-next-event', n_clicks=0,
                         style={
                             'font-size': '14px',
                             "margin-left": "15px",
                             "background-color": main_color,
                             "background-image":
                                 f"-webkit-gradient(linear, left top, left bottom, "
                                 f"from({main_color}), to({secondary_color}))",
                         }, ),
        ],
    )


def create_dates_navigation_widget():

    return html.Div(
        [
            html.Br(),
            dmc.Checkbox(
                id="navigate-dates-fast",
                label="Navigate between dates with arrows",
                mb=10,
                disabled=False,
                checked=False,

            ),
            html.Br(),
            CustomButton("Show Data", id="show-raw-data", n_clicks=0),
            CustomButton('<<', id='load-previous-dates', n_clicks=0,
                         style={
                             'font-size': '14px',
                             "margin-left": "15px",
                             "background-color": main_color,
                             "background-image":
                                 f"-webkit-gradient(linear, left top, left bottom, "
                                 f"from({main_color}), to({secondary_color}))",
                         }, ),
            CustomButton('>>', id='load-next-dates', n_clicks=0,
                         style={
                             'font-size': '14px',
                             "margin-left": "15px",
                             "background-color": main_color,
                             "background-image":
                                 f"-webkit-gradient(linear, left top, left bottom, "
                                 f"from({main_color}), to({secondary_color}))",
                         }, ),
        ],
    )


def create_show_data_widget(data_type, event_id=None, machine_events=None, event_type_str=''):
    if data_type == 'raw-data':
        sub_widgets = html.Div([html.Br(),
                                create_dates_navigation_widget(),
                                html.Br(),
                                create_download_widget()])
    elif data_type == 'events-data':
        sub_widgets = html.Div([create_events_navigation_widget(machine_events, event_id, event_type_str),
                                html.Br(),
                                create_download_widget()])
    else:
        sub_widgets = []
    show_data_widget = dcc.Loading(
        id="loading-menu-element",
        children=sub_widgets,
        type="dot",
        color=secondary_color
    )
    return show_data_widget


def create_sidebar_children(machines, selected_machine,
                            pipeline_versions, pipeline_selected_versions,
                            only_manual_mode):
    machines_df = get_machines_metadata_from_csv() if only_manual_mode else get_machines_metadata_from_db()
    open_form_button, versions_modal = create_configurations_form(pipeline_versions, pipeline_selected_versions)
    side_bar_children_elements = [
        open_form_button,
        versions_modal,
        html.Br(),
        html.Br(),
        dbc.Label("Select machine to investigate", size=12, color=main_color),
        dcc.Dropdown(machines, selected_machine, id="machine-dropdown"),
        html.Br(),
        create_off_canvas_machines_metadata(machines_df),
        html.Br(),
        create_full_load_data_widget(),
        html.Div(
            [
                html.Div(
                    id="metadata-div",
                    children=[])
            ]
        ),
    ]
    return side_bar_children_elements


def create_sidebar_metadata(machine_id, selected_machine_df, machine_events, start_timestamp, end_timestamp, data_type, label_type=None):
    dates_str = "Event Timestamps" if data_type == "events-data" else "Select Timestamps"
    event_type = 1 if label_type is None else label_type
    event_type_str = get_event_type_str(machine_events, 0) if machine_events is not None else ""

    side_bar_children_elements = [html.Br()]
    if data_type == "events-data":
        side_bar_children_elements += [
            dbc.RadioItems(
                options=[
                    {"label": 'Labeled events', "value": 1},
                    {"label": 'Predicted Events', "value": 2},
                    {"label": 'Manual Events', "value": 3},
                ],
                value=event_type,
                id="checklist-labels-type",
                inline=True
            )]

    side_bar_children_elements += [dbc.Label(dates_str, size=12, color=main_color),
                                   dash_datetimepicker.DashDatetimepicker(
                                       id="date-time-picker", startDate=start_timestamp, endDate=end_timestamp
                                   )]
    side_bar_children_elements += create_metadata_filters_widget(machine_id, selected_machine_df)
    side_bar_children_elements += [create_show_data_widget(data_type,
                                                           1,
                                                           machine_events,
                                                           event_type_str)]

    return side_bar_children_elements


def create_data_sources_metadata_table(metadata_df):
    if metadata_df.empty:
        return dbc.Label("No data sources metadata was stored", size=12, color=main_color)

    return dash_table.DataTable(
        data=metadata_df.to_dict("records"),
        columns=[{"name": i, "id": i} for i in metadata_df.columns],
        # row_selectable=True,
        filter_action="native",
        sort_action='native',
        row_deletable=True,
        style_header={"backgroundColor": main_color, "color": "white"},
        style_cell={"textAlign": "left"},
        page_action='native',
        page_current=0,
        page_size=30,
    )


def create_machines_metadata_table(metadata_df):
    return dash_table.DataTable(
        data=metadata_df.to_dict("records"),
        columns=[{"name": i, "id": i} for i in metadata_df.columns],
        filter_action="native",
        style_header={"backgroundColor": main_color, "color": "white"},
        style_cell={"textAlign": "left"},
    )


def create_off_canvas_data_sources_metadata(selected_machine_df):
    return html.Div(
        [
            dbc.Button(
                "Show Data Sources Metadata",
                id="open-offcanvas-data-sources-metadata",
                size="sm",
                outline=True,
                color="secondary",
                n_clicks=0,
            ),
            dbc.Offcanvas(
                create_data_sources_metadata_table(selected_machine_df),
                id="offcanvas-data-sources-metadata",
                title="Data Sources Metadata",
                is_open=False,
                backdrop=True,
                style={
                    "width": "50%",
                    "display": "inline-block",
                    "overflow-y": "scroll",
                },
            ),
        ]
    )


def create_off_canvas_machines_metadata(machines_metadata_df):
    return html.Div(
        [
            dbc.Button(
                "Show Machines Metadata",
                id="open-offcanvas-machines-metadata",
                size="sm",
                outline=True,
                color="secondary",
                n_clicks=0,
            ),
            dbc.Offcanvas(
                create_machines_metadata_table(machines_metadata_df),
                id="offcanvas-machines-metadata",
                title="Machines Metadata",
                is_open=False,
                backdrop=True,
                style={
                    "width": "30%",
                    "display": "inline-block",
                    "overflow-y": "scroll",
                },
            ),
        ]
    )


def create_tagging_button():
    manual_tag_button = CustomButton(
        "Tag Event",
        id="btn-tag-timeframe",
        color="primary",
        className="me-1",
        style={
            'font-size': '14px',
            "background-color": main_color,
            "background-image":
                f"-webkit-gradient(linear, left top, left bottom, "
                f"from({secondary_color}), to({main_color}))",
            'margin-left': "15px",
        }
    )
    return manual_tag_button


def create_untagging_button():
    manual_untag_button = CustomButton(
        "Untag Event",
        id="btn-untag-timeframe",
        color="primary",
        className="me-1",
        style=dict(display='none')
    )
    return manual_untag_button
