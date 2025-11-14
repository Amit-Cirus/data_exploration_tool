import dash_bootstrap_components as dbc
from dash import html, dcc
from dash_extensions.enrich import DashProxy, ServersideOutputTransform
from loguru import logger as log

from src.callbacks.keter_configurations_callbacks import create_configurations_callbacks
from src.callbacks.keter_dash_predictive_callbacks import create_predictive_callbacks
from src.callbacks.keter_dash_tabs_callbacks import create_tabs_callbacks
from src.data_loaders.keter_data_loader import initialize_data_object
from src.widgets.data_sources_widgets_creation import create_header, create_initial_side_bar
from src.widgets.tabs_creation_utils import create_tabs


def initialize_app(customer_name, machines, selected_machine, data_object, only_manual_mode=False) -> DashProxy:
    log.debug('Application is being initialized')
    initialize_data_object(data_object, machines, only_manual_mode)

    app = DashProxy(
        __name__,
        transforms=[ServersideOutputTransform()],
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        title=f"{customer_name} Dashboard",
    )

    header = create_header(customer_name)

    sidebar = create_initial_side_bar(machines,
                                      selected_machine,
                                      data_object["configurations"]["pipeline_versions_options"],
                                      data_object["configurations"]["pipeline_versions"],
                                      only_manual_mode)

    # # FOR UI WITHOUT TABS USE:
    # content = create_data_sources_analysis_tab_content()
    # app.layout = html.Div([dcc.Location(id="url"), header, sidebar, content])

    # FOR UI WITH TABS USE:
    tabs = create_tabs()
    app.layout = html.Div([dcc.Location(id="url"), header, sidebar, tabs])

    create_configurations_callbacks(app, data_object)
    create_tabs_callbacks(app, data_object)
    create_predictive_callbacks(app, data_object)
    return app
