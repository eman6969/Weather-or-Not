import os
from pathlib import Path
import requests
from datetime import datetime, timedelta


def _load_dotenv_values():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return {}

    values = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def get_api_key():
    dotenv_values = _load_dotenv_values()
    return (
        os.environ.get("OPENWEATHER_API_KEY")
        or os.environ.get("WEATHER_API_KEY")
        or dotenv_values.get("OPENWEATHER_API_KEY")
        or dotenv_values.get("WEATHER_API_KEY")
    )

# --- Weather threshold constants ---
FREEZING_TEMP = 32
COLD_TEMP = 45
HOT_TEMP = 90
EXTREME_HEAT = 100
HIGH_WIND = 25
HIGH_HUMIDITY = 85


def get_greeting(name):
    hour = datetime.now().hour
    if hour < 12:
        return f"Good Morning, {name}"
    elif hour < 18:
        return f"Good Afternoon, {name}"
    else:
        return f"Good Evening, {name}"


def get_location(zip_code):
    """Returns (lat, lon, city, state) or None if invalid ZIP or no network."""
    api_key = get_api_key()
    if not api_key:
        return "MISSING_API_KEY"

    try:
        url = f"https://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={api_key}"
        geo = requests.get(url, timeout=8).json()
        if "lat" not in geo:
            return None
        city  = geo.get("name", "Unknown City")

        # Reverse geocode to get state
        rev_url = f"https://api.openweathermap.org/geo/1.0/reverse?lat={geo['lat']}&lon={geo['lon']}&limit=1&appid={api_key}"
        rev   = requests.get(rev_url, timeout=8).json()
        state = ""
        if rev and isinstance(rev, list):
            state = rev[0].get("state", "")

        return geo["lat"], geo["lon"], city, state
    except Exception:
        return "NO_NETWORK"


def get_weather(lat, lon):
    api_key = get_api_key()
    if not api_key:
        return "MISSING_API_KEY"

    try:
        url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
        return requests.get(url, timeout=8).json()
    except Exception:
        return None


def get_default_data():
    """Returns a safe default dataset when network is unavailable."""
    return {
        "temperature":   "--",
        "feels_like":    "--",
        "humidity":      "--",
        "wind_speed":    "--",
        "wind_gust":     0,
        "pressure":      "--",
        "uv_index":      "--",
        "visibility":    "--",
        "cloud_cover":   "--",
        "dew_point":     "--",
        "condition":     "Unknown",
        "description":   "No network connection",
        "rain_inches":   0,
        "snow_inches":   0,
        "precip_inches": 0,
    }


def get_forecast_tip(temp_high, temp_low, condition, rain, snow):
    tips = []
    if condition == "Snow" and temp_low <= 20:
        tips.append("Extreme cold with snow — dress in heavy layers and limit time outdoors.")
    elif condition == "Snow" and temp_low <= FREEZING_TEMP:
        tips.append("Snow and freezing temps expected — watch for icy roads and sidewalks.")
    elif condition == "Rain" and temp_low <= FREEZING_TEMP:
        tips.append("Freezing rain possible — dangerous black ice risk. Drive with extreme caution.")
    elif condition == "Thunderstorm" and temp_high >= 90:
        tips.append("Storms in extreme heat — stay indoors and hydrate.")
    elif condition == "Thunderstorm":
        tips.append("Thunderstorms expected — avoid outdoor activities and unplug electronics.")
    elif condition == "Rain" and rain > 10:
        tips.append("Heavy rain expected — watch for flooding and allow extra travel time.")
    elif condition == "Rain":
        tips.append("Rain in the forecast — bring an umbrella and allow extra commute time.")
    elif condition == "Snow":
        tips.append("Snow expected — dress warm, drive slow, and watch for slick surfaces.")
    elif temp_high >= 100:
        tips.append("Extreme heat incoming — hydrate early, avoid midday sun, check on pets and elderly.")
    elif temp_high >= 90:
        tips.append("Hot day ahead — stay hydrated and limit outdoor activity during peak hours.")
    elif temp_low <= FREEZING_TEMP:
        tips.append("Freezing overnight temps — protect pipes, plants, and bring pets inside.")
    elif condition == "Clear" and 60 <= temp_high <= 85:
        tips.append("Great conditions ahead — perfect day to plan outdoor activities.")
    elif condition in ("Fog", "Mist"):
        tips.append("Foggy conditions expected — use low-beam headlights and drive carefully.")
    elif condition in ("Dust", "Smoke"):
        tips.append("Poor air quality expected — limit time outdoors, especially for sensitive individuals.")
    else:
        tips.append("Mostly manageable conditions — dress for the temperature and stay aware of changes.")

    if rain > 0 and condition != "Rain":
        tips.append(f"Some rain possible ({rain:.1f} mm).")
    if snow > 0 and condition != "Snow":
        tips.append(f"Some snow possible ({snow:.1f} mm).")

    return " ".join(tips)


def build_alerts(weather):
    """Returns a list of (severity, title, body) tuples. severity: 'danger'|'warning'|'info'|'success'"""
    current = weather["current"]
    temperature = current["temp"]
    humidity    = current["humidity"]
    wind_speed  = current["wind_speed"]
    cloud_cover = current["clouds"]
    uv_index    = current["uvi"]
    condition   = current["weather"][0]["main"]
    rain        = current.get("rain", {}).get("1h", 0)
    visibility  = current["visibility"] / 1609

    alerts = []

    def add(severity, title, body):
        alerts.append((severity, title, body))

    # --- Combo alerts (danger first) ---
    if condition == "Snow" and wind_speed >= 35:
        add("danger", "Blizzard Conditions", "Dangerous travel. Near-zero visibility and drifting snow. Stay indoors.")
    elif condition == "Snow" and wind_speed >= HIGH_WIND:
        add("danger", "Snow + High Wind", "Blowing and drifting snow likely. Use extreme caution driving.")

    if condition == "Snow" and temperature <= 20:
        add("danger", "Extreme Winter Conditions", "Risk of frostbite within minutes. Avoid all outdoor exposure.")

    if condition == "Rain" and temperature <= FREEZING_TEMP:
        add("danger", "Ice Storm Warning", "Freezing rain creating black ice. Do not drive. Salt all walkways immediately.")

    if condition == "Rain" and wind_speed >= HIGH_WIND:
        add("danger", "Heavy Rain + High Wind", "Dangerous driving. Flying debris possible. Secure all outdoor objects.")

    if condition == "Thunderstorm" and wind_speed >= 20:
        add("danger", "Severe Thunderstorm", "Lightning risk high. Seek shelter immediately. Flying debris possible.")

    if condition == "Thunderstorm" and temperature >= 90:
        add("danger", "Thunderstorm + Extreme Heat", "Dangerous storm in extreme heat. Stay indoors. Hydrate before sheltering.")

    if condition == "Thunderstorm" and humidity >= 90:
        add("danger", "Thunderstorm + Flood Risk", "Heavy rain with storm. Watch for flash flooding in low-lying areas.")

    if temperature >= 95 and humidity >= 80:
        add("danger", "Dangerous Heat Index", "Heat index may exceed 115°F. Heatstroke risk is extreme. Stay indoors with A/C.")
    elif temperature >= 85 and humidity >= 70:
        add("warning", "High Heat Index", "Feels significantly hotter due to humidity. Stay hydrated and take breaks in shade.")

    if temperature >= 95 and wind_speed >= HIGH_WIND:
        add("danger", "Extreme Heat + High Wind", "Dangerous fire weather conditions. Avoid open flames outdoors.")

    if temperature <= 40 and wind_speed >= 15:
        add("warning", "Wind Chill Warning", "Feels much colder due to wind. Wear gloves, hat, and cover exposed skin.")

    if condition in ("Fog", "Mist") and rain > 0:
        add("danger", "Fog + Rain", "Extremely low visibility. Use low-beam headlights. Drive at reduced speed or avoid travel.")

    if condition in ("Dust", "Smoke") and wind_speed >= HIGH_WIND:
        add("danger", "Dust/Smoke + High Wind", "Rapidly worsening air quality. Stay indoors. Seal windows and doors.")

    if condition == "Snow" and temperature <= FREEZING_TEMP and humidity >= 80:
        add("warning", "Wet Heavy Snow Warning", "Snow may accumulate on power lines and trees. High risk of power outages.")

    if condition == "Rain" and cloud_cover >= 90 and visibility < 2:
        add("danger", "Rain + Low Visibility", "Extremely poor driving conditions. Headlights on. Reduce speed significantly.")

    # --- Single condition alerts ---
    if temperature <= 20:
        add("danger", "Extreme Cold Alert", "Limit time outdoors. Risk of frostbite. Check on elderly neighbors. Ensure heating systems are working.")
    elif temperature <= FREEZING_TEMP:
        add("warning", "Freeze Warning", "Cover outdoor pipes, bring pets indoors, protect plants, watch for icy roads.")
    elif temperature <= COLD_TEMP:
        add("info", "Cold Weather", "Wear warm layers.")

    if temperature >= 105:
        add("danger", "Extreme Heat Danger", "Heatstroke risk. Stay indoors. Never leave pets or children in vehicles. Wear loose, light clothing.")
    elif temperature >= 95:
        add("warning", "Heat Advisory", "Drink plenty of water. Avoid prolonged sun exposure. Check on elderly and pets.")

    if temperature <= 75 and temperature > COLD_TEMP and temperature > FREEZING_TEMP and temperature > 20:
        add("success", "Mild Weather", "Comfortable conditions.")
    elif temperature <= HOT_TEMP and temperature > 75:
        add("info", "Warm Weather", "Stay hydrated.")
    elif temperature > HOT_TEMP and temperature < 95:
        add("warning", "Extreme Heat", "Drink water, wear light clothes, avoid long sun exposure.")

    if condition == "Rain":
        add("warning", "Rain Advisory", "Carry an umbrella. Allow extra travel time. Roads may be slippery.")
        if humidity >= 90:
            add("danger", "Heavy Rain Conditions", "Watch for flooding in low areas. Avoid driving through standing water.")
    elif condition == "Drizzle":
        add("info", "Light Rain", "Road surfaces may become slick.")

    if condition == "Snow":
        add("warning", "Snow Advisory", "Wear insulated clothing. Drive cautiously. Watch for icy sidewalks.")

    if condition == "Thunderstorm":
        add("danger", "Thunderstorm Alert", "Avoid outdoors. Stay away from tall trees. Unplug sensitive electronics.")

    if condition in ("Fog", "Mist"):
        add("warning", "Low Visibility", "Use low-beam headlights. Drive slowly.")

    if wind_speed >= 40:
        add("danger", "Severe Wind Alert", "Possible power outages. Avoid parking under trees.")
    elif wind_speed >= HIGH_WIND:
        add("warning", "High Wind Warning", "Secure outdoor objects. Caution with high-profile vehicles.")

    if humidity >= HIGH_HUMIDITY:
        add("warning", "High Humidity", "Expect muggy conditions.")

    if condition in ("Dust", "Smoke"):
        add("warning", "Air Quality Alert", "Limit outdoor activity. Sensitive individuals should stay indoors.")

    if condition == "Clear":
        add("success", "Clear Skies", "Good day for outdoor activities.")

    if uv_index >= 10:
        add("danger", "Extreme UV Level", "Avoid midday sun. Wear sunscreen and sunglasses.")
    elif uv_index >= 7:
        add("warning", "High UV Index", "Wear sunscreen and sunglasses.")

    if 60 <= temperature <= 80 and condition == "Clear":
        add("success", "Ideal Weather", "Great conditions for outdoor exercise.")

    if temperature >= 95:
        add("warning", "Pet Safety", "Pavement may burn paws.")
    if temperature <= FREEZING_TEMP:
        add("warning", "Pet Safety", "Bring pets indoors.")

    if 65 <= temperature <= 90 and humidity <= 60 and condition == "Clear":
        add("warning", "High Pollen Conditions", "Allergy sufferers may experience symptoms. Consider antihistamines.")
    elif temperature >= 60 and humidity <= 70 and wind_speed <= 10:
        add("info", "Moderate Pollen Conditions", "Some allergy symptoms possible.")

    if condition in ("Rain", "Snow", "Fog"):
        add("warning", "Driving Caution", "Allow extra stopping distance.")

    # --- New conditions ---
    if condition == "Sleet":
        add("danger", "Sleet Warning", "Freezing rain and ice pellets. Roads extremely slick. Avoid travel if possible.")

    if condition == "Hail":
        add("danger", "Hail Warning", "Cover vehicles and stay indoors. Hail can cause serious injury and property damage.")

    if condition == "Squall":
        add("danger", "Squall Warning", "Sudden violent winds and heavy rain. Secure all outdoor objects immediately.")

    if condition == "Sand":
        add("warning", "Sandstorm Advisory", "Reduced visibility due to blowing sand. Stay indoors and cover face if outside.")

    if condition == "Ash":
        add("danger", "Volcanic Ash Advisory", "Avoid all outdoor activity. Wear mask if going outside. Keep windows closed.")

    if condition == "Hurricane":
        add("danger", "Hurricane Warning", "Extreme danger. Follow evacuation orders. Do not travel unless ordered to evacuate.")

    return alerts


def build_outfit_icons(weather):
    """
    Returns a list of icon filenames (no extension) to show in the 'Going out?' panel.
    CLOTHING is always shown based on temperature.
    ACCESSORIES are conditional based on weather conditions.
    """
    current     = weather["current"]
    temp        = current["temp"]
    feels_like  = current["feels_like"]
    uv_index    = current["uvi"]
    wind_speed  = current["wind_speed"]
    condition   = current["weather"][0]["main"]

    effective_cold = min(temp, feels_like)

    icons = []

    # --- CLOTHING (always exactly one or two items based on temp) ---
    if effective_cold <= 32:
        icons.append("jacket__1_")        # puffer jacket — freezing
        icons.append("scarf")             # scarf — freezing
        icons.append("winter-gloves")     # gloves — freezing
    elif effective_cold <= 45:
        icons.append("jacket__1_")        # puffer jacket — cold
        icons.append("scarf")             # scarf — cold
    elif effective_cold <= 60:
        icons.append("sweater-with-deer") # sweater — mild cold
    else:
        icons.append("t-shirt")           # 60°F+ feels like — just a shirt

    # --- ACCESSORIES (only if conditions warrant) ---

    # Rain/wet gear
    if condition in ("Rain", "Drizzle", "Thunderstorm", "Sleet"):
        icons.append("umbrella")
        icons.append("boots")
        if "jacket__1_" not in icons:     # only add raincoat if not already wearing puffer
            icons.append("jacket")

    # Snow gear (boots if not already from rain)
    if condition == "Snow":
        if "boots" not in icons:
            icons.append("boots")

    # Sun protection
    if uv_index >= 6:
        icons.append("sunglasses")
        icons.append("sunscreen")
    elif condition == "Clear" and temp >= 75:
        icons.append("sunglasses")

    # Deduplicate while preserving order
    seen = set()
    result = []
    for icon in icons:
        if icon not in seen:
            seen.add(icon)
            result.append(icon)

    return result


def build_outlook(weather):
    """Returns list of dicts for the 2-day outlook."""
    days = []
    labels = [
    (datetime.now() + timedelta(days=1)).strftime("%A"),
    (datetime.now() + timedelta(days=2)).strftime("%A")
    ]
    for i, label in enumerate(labels):
        day = weather["daily"][i + 1]
        temp_high   = day["temp"]["max"]
        temp_low    = day["temp"]["min"]
        condition   = day["weather"][0]["main"]
        description = day["weather"][0]["description"]
        rain        = day.get("rain", 0)
        snow        = day.get("snow", 0)
        pop         = int(day.get("pop", 0) * 100)
        rain_inches = rain * 0.03937
        snow_inches = snow * 0.03937
        tip         = get_forecast_tip(temp_high, temp_low, condition, rain, snow)
        days.append({
            "label":       label,
            "temp_high":   int(temp_high),
            "temp_low":    int(temp_low),
            "condition":   condition,
            "description": description,
            "pop":         pop,
            "rain_inches": rain_inches,
            "snow_inches": snow_inches,
            "tip":         tip,
        })
    return days


def get_current_data(weather):
    """Returns a dict of all current condition values."""
    current = weather["current"]
    temperature   = current["temp"]
    feels_like    = current["feels_like"]
    humidity      = current["humidity"]
    wind_speed    = current["wind_speed"]
    wind_gust     = current.get("wind_gust", 0)
    pressure      = current["pressure"]
    uv_index      = current["uvi"]
    visibility    = current["visibility"] / 1609
    cloud_cover   = current["clouds"]
    dew_point     = current["dew_point"]
    condition     = current["weather"][0]["main"]
    description   = current["weather"][0]["description"]
    rain          = current.get("rain", {}).get("1h", 0)
    snow          = current.get("snow", {}).get("1h", 0)
    rain_inches   = rain * 0.03937
    snow_inches   = snow * 0.03937
    precip_inches = (rain + snow) * 0.03937

    return {
        "temperature":   int(temperature),
        "feels_like":    int(feels_like),
        "humidity":      int(humidity),
        "wind_speed":    int(wind_speed),
        "wind_gust":     int(wind_gust),
        "pressure":      int(pressure),
        "uv_index":      int(uv_index),
        "visibility":    round(visibility, 1),
        "cloud_cover":   int(cloud_cover),
        "dew_point":     int(dew_point),
        "condition":     condition,
        "description":   description,
        "rain_inches":   rain_inches,
        "snow_inches":   snow_inches,
        "precip_inches": precip_inches,
    }
