from dash import Input, Output, no_update

from src.data_loaders.keter_raw_data import get_machine_id_by_name
from src.widgets.data_sources_widgets_creation import (
    create_data_sources_analysis_tab_content,
    create_full_load_data_widget_children
)
from src.widgets.machines_statistics_widget_creation import create_machine_statistics_tab_content
from src.widgets.raw_data_widgets_creation import create_data_ingestion_tab_content


def create_tabs_callbacks(app, data):
    @app.callback(
        Output("tab-content", "children"),
        Output("load-data-widget", "children"),
        Output('metadata-div', 'children', allow_duplicate=True),
        [Input("tabs", "active_tab"),
         Input("machine-dropdown", "value"), ])
    def update_tab(active_tab, machine_name):
        print(active_tab)
        machine_id = get_machine_id_by_name(machine_name)
        if active_tab == 'tab-predictive-analytics-data-sources':
            return create_data_sources_analysis_tab_content(), create_full_load_data_widget_children(), []
        if active_tab == 'tab-machine-health':
            return create_machine_statistics_tab_content(data, machine_id), [], []
        if active_tab == 'tab-data-sources-ingestion':
            return create_data_ingestion_tab_content(data, machine_id), [], []
        else:
            return no_update
