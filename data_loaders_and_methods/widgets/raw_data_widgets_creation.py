from dash import dcc, html
from assets.styles import CONTENT_GRAPH_STYLE, TABS_GRAPH_STYLE, INGESTION_GRAPH_STYLE
from src.plotting_utils import create_ingestion_data_plot


def create_ingestion_graph_widget(ingestion_rates_df):
    figure = create_ingestion_data_plot(ingestion_rates_df)

    return [dcc.Graph(id="ingestion_graph",
                      figure=figure,
                      style=INGESTION_GRAPH_STYLE)]


def create_data_ingestion_tab_content(all_data, machine_id):
    if 'ingestion_rates' in all_data:
        machine_df = all_data["ingestion_rates"][machine_id]
        ingestion_widget = create_ingestion_graph_widget(machine_df)
        content = dcc.Loading(
            html.Div([
                html.Br(),
                html.Div(id="machine-plots-element",
                         children=ingestion_widget,
                         style=TABS_GRAPH_STYLE),
            ])
        )
    else:
        content = html.Div(children=[html.Label("Data is not available for selected machine")],
                           style=TABS_GRAPH_STYLE)
    return content
