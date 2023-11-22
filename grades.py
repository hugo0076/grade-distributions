import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd


app = Dash(__name__)
server = app.server

app.layout = html.Div([
    dcc.Input(id='input-field', type='text', placeholder='Enter text here...'),
    html.Button('Save', id='save-button', n_clicks=0),
    dash_table.DataTable(id='table')
])

@app.callback(
    Output('input-field', 'value'),
    Input('save-button', 'n_clicks'),
    State('input-field', 'value')
)
def save_to_csv(n_clicks, value):
    if n_clicks > 0 and value is not None:
        df = pd.DataFrame([value])
        df.to_csv('file.csv', mode='a', header=False, index=False)
        return ''
    else:
        return value

@app.callback(
    Output('table', 'data'),
    Output('table', 'columns'),
    Input('save-button', 'n_clicks')
)
def update_table(n_clicks):
    if n_clicks > 0:
        print('update table')
        df = pd.read_csv('file.csv', header=None)
        data = df.to_dict('records')
        columns = [{"name": str(i), "id": str(i)} for i in df.columns]
        return data, columns
    else:
        print('no update')
        return [], []

if __name__ == '__main__':
    app.run_server(debug=True)
