import dash
from dash import dcc, html, dash_table
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Styling for the main content layout
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

# Define the navigation bar and sidebar
sidebar = html.Div(
    [
        html.H2("Options", className="display-4"),
        html.Hr(),
        html.P(
            "Select the available options:", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/", active="exact"),
                dbc.NavLink("Wind Turbine Map", href="/map", active="exact"),
                dbc.NavLink("Data Overview", href="/data-overview", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style={"position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "16rem", "padding": "2rem 1rem", "background-color": "#f8f9fa"},
)

# Main content
content = html.Div(id="page-content", style=CONTENT_STYLE)

# Define the layout
app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    content
])

# Callback to update the page content based on the navigation bar
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def render_page_content(pathname):
    if pathname == "/":
        return [
            html.H1("Wind Turbine Locations and Capacities", style={'textAlign': 'center'}),
            html.P(children="Welcome to an interactive map of the Canadian Wind Turbine Database. Further background on the data collection can be found here:"),
            html.P(children="https://open.canada.ca/data/en/dataset/79fdad93-9025-49ad-ba16-c26d718cc070")
        ]
    elif pathname == "/map":
        return [
            # Map specific content
            html.H1("Wind Turbine Locations and Capacities"),
            dcc.Graph(
                        id='wind-turbine-map',
                        config={'displayModeBar': True, 'scrollZoom': True, 'modeBarButtonsToAdd': ['select2d', 'lasso2d']},
                        style={'width': '100%', 'height': '60vh'}),
            html.P(id='info-table', style={'width': '100%'})
        ]
    elif pathname == "/data-overview":
        return [
            html.H1("Wind Turbine Data", className="text-center my-4"),
            dash_table.DataTable(
                id='table-overview',
                columns=[{"name": col, "id": col} for col in data.columns],
                data=data.to_dict('records'),
                style_table={'overflowX': 'scroll'},  # If you have many columns, horizontal scroll is enabled.
                filter_action="native",  # Allows filtering of data by user.
                sort_action="native",  # Enables data to be sorted.
                sort_mode="multi",  # Allows multi-column sort.
                page_action="native",  # Pagination of data.
                page_current=0,  # Page number that user is currently on.
                page_size=20,  # Number of rows visible per page.
        )
        ]
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )

# Callbacks for interactive components go here
@app.callback(
    Output('wind-turbine-map', 'figure'),
    [Input('url', 'pathname')]  # Triggered when the URL changes
)
def update_map(pathname):
    # Only update the map if we're on the map page
    if pathname == "/map":
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
    # If we are not on the map page, we don't want to update the figure
    return dash.no_update

@app.callback(
    Output('info-table', 'children'),
    [Input('url', 'pathname'), Input('wind-turbine-map', 'selectedData')]
)
def display_selected_data(pathname, selectedData):
    # Only update the info table when on the map page
    if pathname == "/map":
        # Check if any data points have been selected on the map
        if selectedData is not None:
            indices = [point['pointIndex'] for point in selectedData['points']]
            selected_turbines = data.iloc[indices]
            return dash_table.DataTable(
                data=selected_turbines.to_dict('records'),
                columns=[{"name": i, "id": i} for i in selected_turbines.columns],
                style_table={'height': '300px', 'overflowY': 'auto'}
            )
        else:
            # Return a message prompting the user to select data if none is selected
            return "Hover over turbines for a quick view or select turbines using the lasso tool to see their details."
    # If we are not on the map page, we don't want to update the info table
    return dash.no_update

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
