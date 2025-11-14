from dash import html
import dash_bootstrap_components as dbc

from assets.styles import *


def create_tabs_children():
    return [
        dbc.Tab(label='Data Sources AI Analysis',
                tab_id="tab-predictive-analytics-data-sources",
                active_tab_class_name="custom-tab--selected",
                tab_class_name="custom-tab"
                ),
        dbc.Tab(label='Data Sources Ingestion',
                tab_id="tab-data-sources-ingestion",
                active_tab_class_name="custom-tab--selected",
                tab_class_name="custom-tab"
                ),

        dbc.Tab(label='Machine Exploration',
                tab_id="tab-machine-health",
                active_tab_class_name="custom-tab--selected",
                tab_class_name="custom-tab"
                ),
    ]


def create_tabs():
    tabs = html.Div([
        dbc.Row([
            dbc.Col(
                dbc.Tabs(create_tabs_children(), id="tabs",
                         active_tab="tab-predictive-analytics-data-sources",
                         class_name="custom-tabs-container",
                         style=TABS_STYLE,
                         ),
                width={"size": 12, "order": 2},  # Adjust the size as needed
            ),
            dbc.Col(
                html.Div(id="tab-content"),

                width={"size": 12, "order": 2},  # Adjust the size as needed
            ),
        ]),
    ])
    return tabs
