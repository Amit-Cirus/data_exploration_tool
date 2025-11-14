import os

from dash import dcc, html

from assets.styles import *
from src.plotting_utils import plot_timeframes_by_count, plot_timeframes_by_time


def create_machine_timeframes_widget(machine_id, machine_timeframes_df, group_by='time', export=False):
    if group_by == 'count':
        fig = plot_timeframes_by_count(machine_timeframes_df)

    if group_by == 'time':
        calculate_good = False if machine_id == '4' else True
        fig = plot_timeframes_by_time(machine_timeframes_df, calculate_good=calculate_good)

    if export:
        os.makedirs("output", exist_ok=True)
        file_name = os.path.join("output", f"machine_{machine_id}_{group_by}_distribution.html")
        fig.write_html(file_name)

    return [dcc.Graph(id="pie-graph",
                      figure=fig,
                      style=CONTENT_GRAPH_STYLE)]


def create_machine_statistics_tab_content(all_data, machine_id):
    if 'events' in all_data:
        machine_df = all_data["events"]['labeled'][machine_id]['full']
        machine_exploration_widget = create_machine_timeframes_widget(machine_id, machine_df)
        content = dcc.Loading(
            html.Div([
                html.Br(),
                html.Div(id="machine-plots-element",
                         children=machine_exploration_widget,
                         style=TABS_GRAPH_STYLE),
            ])
        )
    else:
        content = html.Div(children=[html.Label("Data is not available for selected machine")],
                           style=TABS_GRAPH_STYLE)
    return content
