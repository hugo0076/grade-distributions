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

NOT_PDF = -1
FILE_DUPE = -2
HASH_FP = "./file_hashes.csv"


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
        dbc.Modal(
            [
                dbc.ModalHeader("File Upload"),
                dbc.ModalBody(id="modal_body"),
                dbc.ModalFooter(dbc.Button("Close", id="close", className="ml-auto")),
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
        html.Div(id="n_records_store", style={"display": "none"}),
        html.Div(id='refresh', style={'display': 'none'}),
        dcc.Store(id='unique_dict_store'),
        dcc.Store(id='subject_data_store'),
    ],
    fluid=True,
)

# Load the data from the CSV file on initial page load/subsequent refreshes
@app.callback(
    Output('subject_data_store', 'data'),
    Output("subject-year-dropdown", "options"),
    Output("unique_dict_store", "data"),
    Input('refresh', 'children'),
)
def update_data(dummy):
    print('update_data')
    data, unique_subject_years = read_subject_data()
    return data.to_dict("records"), list(unique_subject_years.keys()), unique_subject_years


@app.callback(
    Output('main-graph', 'figure'),
    Input('subject-year-dropdown', 'value'),
    State('unique_dict_store', 'data'),
    State('subject_data_store', 'data'),
    prevent_initial_call=True
)
def update_graph(selected_subject_year, subject_year_dict, scores):
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
        return fig
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
    Input("close", "n_clicks"),
    Input("n_records_store", "children"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def toggle_modal(contents, n_clicks, num_records, filename):
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
