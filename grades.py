import io
import csv
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output, State, Dash
import plotly.graph_objs as go
import plotly.figure_factory as ff
import plotly.express as px
import pandas as pd
import base64
import fitz  # PyMuPDF
from util import extract_subject_data, store_subject_data, read_subject_data
import hashlib
from pathlib import Path

NOT_PDF = -1
FILE_DUPE = -2

THIS_FOLDER = str(Path(__file__).parent.resolve())

HASH_FP = THIS_FOLDER + "/file_hashes.csv"


app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

app.layout = dbc.Container(
    [   
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "UniMelb Grade Distributions",
                            style={"textAlign": "center", "margin": "auto"},
                        )
                    ],
                    width=12,
                    className="mx-auto p-4",
                )
            ],
            align="center",
            justify="center",
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                dcc.Loading(
                                    id="loading",
                                    type="circle",
                                    children=[
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
                            id="subject-year-dropdown-div",
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
                                "width": "60%",
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

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                "Made with ❤️ by ",
                                html.A("hugo", href="https://www.linkedin.com/in/hugo-lyons-keenan-40708bbb/"),
                            ],
                            style={"textAlign": "center", "margin": "auto"},
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
                dbc.ModalBody(id="modal_body"),
            ],
            id="modal",
        ),
        dbc.Modal(
            [
                dbc.ModalHeader("File Upload Error"), 
                dbc.ModalBody(id="error_modal_body"),
            ],
            id="error_modal",
        ),
        dbc.Modal(
            [
                dbc.ModalHeader("Please Contribute!"), 
                dbc.ModalBody(id="pls_modal_body"),
            ],
            id="pls_modal",
        ),
        html.Div(id="n_records_store", style={"display": "none"}),
        html.Div(id='refresh', style={'display': 'none'}),
        html.Div(id='n_graphs_shown', style={'display': 'none'}, children=0),
        dcc.Store(id='unique_dict_store'),
        dcc.Store(id='subject_data_store'),
    ],
    fluid=True,
)

# Load the data from the CSV file on initial page load/subsequent refreshes
@app.callback(
    Output('subject_data_store', 'data'),
    Output("subject-year-dropdown", "options"),
    Output("subject-year-dropdown", "value"),
    Output("unique_dict_store", "data"),
    Input('refresh', 'children'),
)
def update_data(dummy):
    print('update_data')
    data, unique_subject_years = read_subject_data()
    selected_value = list(unique_subject_years.keys())[0] if unique_subject_years else None
    return data.to_dict("records"), list(unique_subject_years.keys()), selected_value, unique_subject_years


@app.callback(
    Output("pls_modal", "is_open"),
    Output("pls_modal_body", "children"),
    Input("n_graphs_shown", "children"),
)
def toggle_pls_modal(n_graphs_shown):
    if n_graphs_shown > 0 and n_graphs_shown % 3 == 0:
        return True, f"Hey! You've viewed {n_graphs_shown} subjects. Please consider contributing your own data to the project. <3"
    else:
        return False, ""

@app.callback(
    Output('main-graph', 'figure'),
    Output('n_graphs_shown', 'children'),
    Input('subject-year-dropdown', 'value'),
    State('unique_dict_store', 'data'),
    State('subject_data_store', 'data'),
    State('n_graphs_shown', 'children'),
    prevent_initial_call=True
)
def update_graph_and_alert(selected_subject_year, subject_year_dict, scores, n_graphs_shown):
    if selected_subject_year is not None:
        year, subject_code, subject_name = subject_year_dict[selected_subject_year]
        df = pd.DataFrame(scores)
        # get the scores for the selected subject-year
        scores = df.loc[(df["subject_code"] == subject_code) & (df["year"] == year)]
        # create the distribution plot
        fig = px.histogram(
            scores,
            x="score",
            marginal="violin",
            hover_data=["score"],
            color_discrete_sequence=["indianred"],
            opacity=0.75,
            range_x=[30, 100],
            nbins=70,
        )
        # set title and axis labels
        fig.update_layout(
            title_text=f"{subject_code} - {subject_name} ({year})",
            xaxis_title_text="Score",
        )
        print(n_graphs_shown + 1)
        return fig, n_graphs_shown + 1
    else:
        return dash.no_update

@app.callback(
    Output("n_records_store", "children"),
    Output('refresh', 'children'),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def read_file(contents, filename):
    """
    Reads the uploaded file and extracts the subject data. Stores the subject data in a CSV file.
    """
    if contents is not None:
        # read the file
        content_type, content_string = contents.split(",")
        if "pdf" not in content_type:
            print("File not PDF")
            return NOT_PDF, dash.no_update

        # check if the file has already been uploaded
        file_hash = hashlib.sha256(content_string.encode()).hexdigest()
        file_hashes = pd.read_csv(HASH_FP, header=None)[0].tolist()
        if file_hash in file_hashes:
            print("File already uploaded")
            return FILE_DUPE, dash.no_update
        else:
            # store the file hash
            with open(HASH_FP, "a") as f:
                writer = csv.writer(f)
                writer.writerow([file_hash])

        # decode the file contents
        decoded = base64.b64decode(content_string)
        pdf_file = io.BytesIO(decoded)
        doc = fitz.open("pdf", pdf_file.read())
        extracted_text = "".join([page.get_text() for page in doc])
        doc.close()

        # extract the subject data from the file
        records = extract_subject_data(extracted_text)
        num_records = len(records)
        print(num_records)
        # store the subject data
        store_subject_data(records)
        return num_records, 'refresh'
    else:
        return 0, dash.no_update


@app.callback(
    Output("error_modal", "is_open"),
    Output("error_modal_body", "children"),
    Input("n_records_store", "children"),
)
def toggle_error_modal(num_records):
    print(dash.callback_context.triggered)
    if num_records == NOT_PDF:
        return True, "File must be a PDF."
    elif num_records == FILE_DUPE:
        return True, "File has already been uploaded."
    else:
        return False, ""

@app.callback(
    Output("modal", "is_open"),
    Output("modal_body", "children"),
    Input("upload-data", "contents"),
    Input("n_records_store", "children"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def toggle_modal(contents, num_records, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, ""
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "upload-data" and contents is not None and num_records > 0:
            message = f"File {filename} uploaded successfully. {num_records} records were extracted."
            return True, message
        else:
            return False, ""


if __name__ == "__main__":
    app.run_server(debug=True)
