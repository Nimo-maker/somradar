import os
import requests
import pandas as pd
import folium
import matplotlib.pyplot as plt
import io
import base64
from shiny import App, ui, render, reactive

# === STEP 1: Fetch Somalia Flights ===
def fetch_opensky_flights(path="flights.csv"):
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        states = data.get("states", [])
        if not states:
            return False
        columns = [
            "icao24", "callsign", "origin_country", "time_position", "last_contact",
            "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
            "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
            "spi", "position_source"
        ]
        df = pd.DataFrame(states, columns=columns)
        df = df[df["on_ground"] == False]
        df = df[df["latitude"].notnull() & df["longitude"].notnull()]
        df = df[(df["latitude"].between(-2, 12)) & (df["longitude"].between(40, 52))]
        if df.empty:
            return False
        flights = df[["callsign", "origin_country", "latitude", "longitude", "velocity"]].copy()
        flights.rename(columns={
            "callsign": "flightnumber",
            "origin_country": "destination",
            "velocity": "price"
        }, inplace=True)
        flights["date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        flights["destination"] = "Somalia (Airspace)"
        flights.to_csv(path, index=False)
        return True
    return False

# === STEP 2: Load or Create Fallback Data ===
def load_flights():
    path = "flights.csv"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        success = fetch_opensky_flights()
        if not success:
            return pd.DataFrame([{
                "flightnumber": "N/A",
                "destination": "No Flights",
                "latitude": 0.0,
                "longitude": 0.0,
                "price": 0,
                "date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
    df = pd.read_csv(path)
    df.columns = df.columns.str.lower()
    return df

# === STEP 3: Build UI ===
app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.link(rel="icon", type="image/x-icon", href="favicon.ico")
    ),
    ui.panel_title("Somalia Airspace Monitor ✈"),
    ui.tags.img(src="logo.png", style="height:60px; margin-bottom:10px;"),
    ui.tags.p("Real-time aircraft currently flying over Somalia's airspace."),
    ui.input_action_button("refresh", "🔄 Refresh Flights"),
    ui.output_table("flight_table"),
    ui.output_ui("map_output"),
    ui.output_ui("chart_output"),
    ui.hr(),
    ui.h5("Built by Nima Fidaar © 2025 – Powered by Sigma Inc, OSINT")
)

# === STEP 4: Server Logic ===
def server(input, output, session):
    flights = reactive.Value(load_flights())

    # Manual refresh
    @reactive.effect
    @reactive.event(input.refresh)
    def _():
        if fetch_opensky_flights():
            flights.set(load_flights())

    # 🔁 Auto-refresh every 5 minutes
    @reactive.effect
    def auto_refresh():
        reactive.invalidate_later(300_000)
        if fetch_opensky_flights():
            flights.set(load_flights())

    @output
    @render.table
    def flight_table():
        df = flights()
        return df.sort_values(by="price", ascending=False).head(10)

    @output
    @render.ui
    def map_output():
        df = flights()
        m = folium.Map(location=[4.5, 45.0], zoom_start=5)
        for _, row in df.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=f"{row['flightnumber']} ({row['destination']})\nSpeed: {row['price']} km/h",
                tooltip=row["flightnumber"]
            ).add_to(m)
        return ui.HTML(m._repr_html_())

    @output
    @render.ui
    def chart_output():
        df = flights()
        fig, ax = plt.subplots(figsize=(6, 4))
        top = df.sort_values(by="price", ascending=False).head(10)
        ax.barh(top["flightnumber"], top["price"], color="skyblue")
        ax.set_xlabel("Speed (km/h)")
        ax.set_title("Top 10 Aircraft Speeds over Somalia")
        ax.invert_yaxis()
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close(fig)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return ui.HTML(f'<img src="data:image/png;base64,{encoded}" style="max-width:100%;">')

# === STEP 5: Launch App ===
app = App(app_ui, server, static_assets=os.path.join(os.path.dirname(__file__), "."))

