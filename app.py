import dash
from dash import dcc, html, dash_table
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import flask

# Function to clean the wind turbine data
def clean_wind_turbine_data(file_path):
    data = pd.read_csv(file_path)
    data['Turbine rated capacity (kW)'] = pd.to_numeric(data['Turbine rated capacity (kW)'], errors='coerce')
    data['Commissioning date'] = pd.to_datetime(data['Commissioning date'], errors='coerce')
    numeric_cols = data.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_cols:
        data[col].fillna(data[col].mean(), inplace=True)
    categorical_cols = data.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        data[col].fillna(data[col].mode()[0], inplace=True)
    return data

# Path to the data file (update the path if the app is deployed or run from a different directory)
file_path = r'data/turbine_data.csv'  # Update this to the correct path when deploying
data = clean_wind_turbine_data(file_path)

# Dash app setup
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Wind Turbine Locations and Capacities"),
    dcc.Graph(
        id='wind-turbine-map',
        config={'displayModeBar': True, 'scrollZoom': True, 'modeBarButtonsToAdd': ['select2d', 'lasso2d']},
        style={'width': '30%', 'height': '60vh'}
    ),
    html.Div(id='info-table', style={'width': '30%'}),
    html.Button("Download as CSV", id="download-csv", style={'display': 'none'}),
    
    # Navigation bar on the left
    html.Div([
        html.Button("Display Dataset", id="display-data-btn", n_clicks=0)
    ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top'}),

    # Content area on the right
    html.Div([
        html.Button("Download as CSV", id="download-csv-btn", style={'display': 'none'}),
        dcc.Download(id="download-dataframe-csv"),
        html.Div(id="data-table-container")
    ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        
])

@app.callback(
    Output('wind-turbine-map', 'figure'),
    Input('wind-turbine-map', 'id')
)
def update_map(_):
    # Creating the hover text with more information
    hover_text = [
        f"Identifier: {id}<br>"
        f"Capacity: {cap} kW<br>"
        f"Manufacturer: {man}<br>"
        f"Model: {mod}<br>"
        f"Commissioned: {date}"
        for id, cap, man, mod, date in zip(
            data['Turbine identifier'],
            data['Turbine rated capacity (kW)'],
            data['Manufacturer'],
            data['Model'],
            data['Commissioning date'].dt.strftime('%Y-%m-%d')  # Formatting the date
        )
    ]

    # Creating the bubble map
    fig = go.Figure(data=go.Scattergeo(
        lon = data['Longitude'],
        lat = data['Latitude'],
        text = hover_text,
        marker = dict(
            size = data['Turbine rated capacity (kW)'] / 10,  # Scaling the bubble size
            color = 'blue',
            line_color='rgb(40,40,40)',
            line_width=0.5,
            sizemode = 'area'
        ),
        hoverinfo = 'text'  # Ensure this is set to 'text' to display custom hover text
    ))

    fig.update_layout(
        title = 'Wind Turbines by Capacity',
        geo = dict(
            scope = 'north america',
            landcolor = 'rgb(217, 217, 217)',
        )
    )
    return fig
'''
@app.callback(
    Output('info-table', 'children'),
    [Input('wind-turbine-map', 'clickData')]
)

def display_click_data(clickData):
    if clickData is not None:
        idx = clickData['points'][0]['pointIndex']
        turbine = data.iloc[idx]
        return dash_table.DataTable(
            data=[turbine.to_dict()],
            columns=[{"name": i, "id": i} for i in turbine.index],
            style_table={'height': '300px', 'overflowY': 'auto'}
        )
    return "Click on a turbine to see more details."
'''
@app.callback(
    [Output('info-table', 'children'),
     Output("download-csv", "style")],
    [Input('wind-turbine-map', 'selectedData'),
     Input("download-csv", "n_clicks")]
)
def display_selected_data(selectedData, n_clicks_download):
    # Check if any data points have been selected on the map
    if selectedData is not None:
        indices = [point['pointIndex'] for point in selectedData['points']]
        selected_turbines = data.iloc[indices]
        table = dash_table.DataTable(
            data=selected_turbines.to_dict('records'),
            columns=[{"name": i, "id": i} for i in selected_turbines.columns],
            style_table={'height': '300px', 'overflowY': 'auto'}
        )
        return table, {'display': 'block'}  # Show the download button when data is selected
    # Hide the download button when no data is selected or on initial load
    return "Select turbines using the lasso tool to see their details.", {'display': 'none'}

@app.callback(
    [Output("data-table-container", "children"),
     Output("download-csv-btn", "style")],
    [Input("display-data-btn", "n_clicks")],
    prevent_initial_call=True
)
def display_data(n_clicks):
    if n_clicks > 0:
        table = dash_table.DataTable(
            data=data.to_dict('records'),
            columns=[{"name": i, "id": i} for i in data.columns],
            page_size=10,  # Set this as needed
            style_table={'height': '300px', 'overflowY': 'auto'}
        )
        return table, {'display': 'block'}
    raise PreventUpdate

@app.callback(
    Output("download-dataframe-csv", "data"),
    [Input("download-csv-btn", "n_clicks")],
    prevent_initial_call=True
)
def download_csv(n_clicks):
    if n_clicks > 0:
        return dcc.send_data_frame(data.to_csv, filename="wind_turbine_data.csv")
    raise PreventUpdate

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
