import io
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output, State, Dash
import plotly.graph_objs as go
import pandas as pd
import base64
import fitz  # PyMuPDF
from util import extract_subject_data, store_subject_data, read_subject_data

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                dcc.Upload(
                                    id="upload-data",
                                    children=html.Div(
                                        ["Upload Transcript", html.A(" (Select Files)")]
                                    ),
                                    style={
                                        "width": "100%",
                                        "height": "60px",
                                        "lineHeight": "60px",
                                        "borderWidth": "1px",
                                        "borderStyle": "dashed",
                                        "borderRadius": "5px",
                                        "textAlign": "center",
                                        "margin": "10px",
                                    },
                                    multiple=False,
                                )
                            ],
                            style={"width": "75%", "margin": "auto", "align": "center"},
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                dcc.Dropdown(
                                    [],
                                    id="subject-year-dropdown",
                                    placeholder="Select a subject",
                                    style={"backgroundColor": "#888", "color": "#000"},
                                ),
                                html.Div(id="dd-output-container"),
                            ],
                            style={"width": "75%", "margin": "auto", "align": "center"},
                        )
                    ],
                    width=6,
                    className="text-right",
                ),
            ],
            align="center",
            justify="center",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [dcc.Graph(id="main-graph", figure=go.Figure())],
                            style={
                                "width": "500px",
                                "margin": "auto",
                                "align": "center",
                            },
                        )
                    ],
                    width=12,
                    className="mx-auto p-4",
                )
            ],
            align="center",
            justify="center",
        ),
        dbc.Modal(
            [
                dbc.ModalHeader("File Upload"),
                dbc.ModalBody(id="modal-body"),
                dbc.ModalFooter(dbc.Button("Close", id="close", className="ml-auto")),
            ],
            id="modal",
        ),
        html.Div(id="hidden-div", style={"display": "none"}),
    ],
    fluid=True,
)


@app.callback(
    Output("hidden-div", "children"),
    Output("subject-year-dropdown", "options"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def read_file(contents, filename):
    """
    Reads the uploaded file and extracts the subject data. Stores the subject data in a CSV file.
    """
    if contents is not None:
        content_type, content_string = contents.split(",")
        if "pdf" not in content_type:
            print("File not PDF")
            return dash.no_update, dash.no_update
        decoded = base64.b64decode(content_string)
        pdf_file = io.BytesIO(decoded)
        doc = fitz.open("pdf", pdf_file.read())
        extracted_text = "".join([page.get_text() for page in doc])
        doc.close()
        records = extract_subject_data(extracted_text)
        num_records = len(records)
        print(num_records)
        print(store_subject_data(records))
        data, unique_subject_years = read_subject_data()
        return num_records, list(unique_subject_years.keys())
    else:
        return 0, dash.no_update

@app.callback(
    Output("modal", "is_open"),
    Output("modal-body", "children"),
    Input("upload-data", "contents"),
    Input("close", "n_clicks"),
    Input("hidden-div", "children"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def toggle_modal(contents, n_clicks, num_records, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, ""
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "upload-data" and contents is not None:
            message = f"File {filename} uploaded successfully. {num_records} records were extracted."
            return True, message
        else:
            return False, ""


if __name__ == "__main__":
    app.run_server(debug=True)
