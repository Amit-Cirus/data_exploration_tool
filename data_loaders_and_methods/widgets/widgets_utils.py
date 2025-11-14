from dash import html
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, dash_table, Input, Output, State, callback

from assets.styles import UPLOAD_FILES_STYLE
from src.keter_globals import main_color, secondary_color


def CustomButton(*args, **kwargs):
    default_color = main_color
    kwargs.setdefault(
        "style",
        {
            'font-size': '14px',
            "background-color": default_color,
            "background-image": f"-webkit-gradient(linear, left top, left bottom, "
                                f"from({main_color}), to({secondary_color}))",
        },
    )
    return dbc.Button(*args, **kwargs)


def create_upload_component(component_id, component_type, max_files=1):
    return html.Div(
        children=[
            dcc.Upload(
                id=component_id,
                children=html.Div([
                    f'Drag and Drop {component_type} files or ',
                    html.A('Select Files')
                ]),
                multiple=True if max_files>1 else False,
                style=UPLOAD_FILES_STYLE
            )
        ],
    )
