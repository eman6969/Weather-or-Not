import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not API_KEY:
    print("Error: OPENWEATHER_API_KEY not found. Make sure your .env file exists.")
    exit()

ZIP = input("Enter your ZIP code: ")

# --- Weather threshold constants ---
FREEZING_TEMP = 32
COLD_TEMP = 45
HOT_TEMP = 90
EXTREME_HEAT = 100

HIGH_WIND = 25
HIGH_HUMIDITY = 85


# --- Convert ZIP to latitude/longitude ---
geo_url = f"https://api.openweathermap.org/geo/1.0/zip?zip={ZIP},US&appid={API_KEY}"
geo = requests.get(geo_url).json()

if "lat" not in geo:
    print("Invalid ZIP Code")
    exit()

lat = geo["lat"]
lon = geo["lon"]


# --- Get weather data ---
weather_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial"
weather = requests.get(weather_url).json()


# --- Extract data ---
temperature = weather["current"]["temp"]
feels_like = weather["current"]["feels_like"]
humidity = weather["current"]["humidity"]
wind_speed = weather["current"]["wind_speed"]
pressure = weather["current"]["pressure"]
uv_index = weather["current"]["uvi"]
visibility = weather["current"]["visibility"]
cloud_cover = weather["current"]["clouds"]
dew_point = weather["current"]["dew_point"]

condition = weather["current"]["weather"][0]["main"]
description = weather["current"]["weather"][0]["description"]

wind_gust = weather["current"].get("wind_gust", 0)
rain = weather["current"].get("rain", {}).get("1h", 0)
snow = weather["current"].get("snow", {}).get("1h", 0)

precipitation = rain + snow

tomorrow_temp = weather["daily"][1]["temp"]["day"]
tomorrow_condition = weather["daily"][1]["weather"][0]["main"]
tomorrow_rain = weather["daily"][1].get("rain", 0)


###Display all weather information###

print("------ WEATHER DATA ------")

print("Temperature:", int(temperature), "°F")
print("Feels Like:", int(feels_like), "°F")
print("Humidity:", int(humidity), "%")
print("Wind Speed:", int(wind_speed), "mph")
print("Wind Gust:", int(wind_gust), "mph")
print("Pressure:", int(pressure), "hPa")
print("UV Index:", int(uv_index))
print("Visibility:", int(visibility), "m")
print("Cloud Cover:", int(cloud_cover), "%")
print("Dew Point:", int(dew_point), "°F")

print("Condition:", condition)
print("Description:", description)

print("Rain (1h):", int(rain), "mm")
print("Snow (1h):", int(snow), "mm")
print("Total Precipitation:", int(precipitation), "mm")

print("Tomorrow Temp:", int(tomorrow_temp))
print("Tomorrow Condition:", tomorrow_condition)

print("--------------------------")


# ----------------------------
# WEATHER LOGIC
# ----------------------------

###Temperature logic###

if temperature <= 32:
    print("FREEZE WARNING")
    print("Cover outdoor pipes.")
    print("Bring pets indoors.")
    print("Protect sensitive plants.")
    print("Wear heavy layered clothing.")
    print("Watch for icy roads.")

if temperature <= 20:
    print("EXTREME COLD ALERT")
    print("Limit time outdoors.")
    print("Risk of frostbite.")
    print("Check on elderly neighbors.")
    print("Ensure heating systems are working.")

elif temperature <= COLD_TEMP:
    print("\nCOLD WEATHER")
    print("Wear warm layers.")

if temperature <= 40 and wind_speed >= 15:
    print("WIND CHILL WARNING")
    print("Feels colder due to wind.")
    print("Wear gloves and a hat.")

if temperature >= 95:
    print("HEAT ADVISORY")
    print("Drink plenty of water.")
    print("Avoid prolonged sun exposure.")
    print("Check on elderly and pets.")

if temperature >= 105:
    print("EXTREME HEAT DANGER")
    print("Heatstroke risk.")
    print("Stay indoors if possible.")
    print("Never leave pets or children in vehicles.")

if temperature >= 85 and humidity >= 70:
    print("HIGH HEAT INDEX")
    print("Feels hotter due to humidity.")
    print("Stay hydrated.")
    print("Take breaks in shade.")

elif temperature <= 75:
    print("\nMILD WEATHER")
    print("Comfortable conditions.")

elif temperature <= HOT_TEMP:
    print("\nWARM WEATHER")
    print("Stay hydrated.")

else:
    print("\nEXTREME HEAT")
    print("Drink water, wear light clothes, avoid long sun exposure.")


###Rain logic###
if condition == "Rain":
    print("\nRAIN EXPECTED")
    print("Bring umbrella and drive carefully.")

elif condition == "Drizzle":
    print("\nLIGHT RAIN")
    print("Roads may be slick.")

if condition == "Rain":
    print("RAIN ADVISORY")
    print("Carry an umbrella.")
    print("Allow extra travel time.")
    print("Roads may be slippery.")

if condition == "Drizzle":
    print("LIGHT RAIN")
    print("Road surfaces may become slick.")

if condition == "Rain" and humidity >= 90:
    print("HEAVY RAIN CONDITIONS")
    print("Watch for flooding in low areas.")
    print("Avoid driving through standing water.")

###Snow###

if condition == "Snow":
    print("SNOW ADVISORY")
    print("Wear insulated clothing.")
    print("Drive cautiously.")
    print("Watch for icy sidewalks.")

if condition == "Snow" and wind_speed >= 30:
    print("BLIZZARD CONDITIONS")
    print("Avoid travel if possible.")
    print("Expect low visibility.")


###Storm###

if condition == "Thunderstorm":
    print("THUNDERSTORM ALERT")
    print("Avoid outdoor activity.")
    print("Stay away from tall trees.")
    print("Unplug sensitive electronics.")

if condition == "Thunderstorm" and wind_speed >= 20:
    print("SEVERE STORM CONDITIONS")
    print("Lightning risk high.")
    print("Seek shelter immediately.")


###Fog###

if condition == "Fog" or condition == "Mist":
    print("LOW VISIBILITY")
    print("Use low-beam headlights.")
    print("Drive slowly.")


###Wind###

if wind_speed >= 25:
    print("HIGH WIND WARNING")
    print("Secure outdoor objects.")
    print("Use caution driving high-profile vehicles.")

if wind_speed >= 40:
    print("SEVERE WIND ALERT")
    print("Possible power outages.")
    print("Avoid parking under trees.")


###Humidity###

if humidity >= HIGH_HUMIDITY:
    print("\nHIGH HUMIDITY")
    print("Expect muggy conditions.")

if condition == "Dust" or condition == "Smoke":
    print("AIR QUALITY ALERT")
    print("Limit outdoor activity.")
    print("Sensitive individuals should stay indoors.")

if condition == "Clear":
    print("CLEAR SKIES")
    print("Good day for outdoor activities.")

###UV Index###

if uv_index >= 7:
    print("HIGH UV INDEX")
    print("Wear sunscreen.")
    print("Wear sunglasses.")

if uv_index >= 10:
    print("EXTREME UV LEVEL")
    print("Avoid midday sun.")

###Combined Weather Situations###

if condition == "Rain" and wind_speed >= 20:
    print("RAIN + WIND CONDITIONS")
    print("Use caution driving.")
    print("Strong gusts possible.")

if condition == "Snow" and temperature <= 20:
    print("EXTREME WINTER CONDITIONS")
    print("Risk of frostbite.")

###Outdoor Activities###

if temperature >= 60 and temperature <= 80 and condition == "Clear":
    print("IDEAL WEATHER")
    print("Great conditions for outdoor exercise.")

###Pet Safety###

if temperature >= 95:
    print("PET SAFETY WARNING")
    print("Pavement may burn paws.")

if temperature <= 32:
    print("PET SAFETY WARNING")
    print("Bring pets indoors.")

###Allergy Conditions### Does not pull pollen information but shows conditions for pollen to possibly be high or low

if temperature >= 65 and temperature <= 90 and humidity <= 60 and condition == "Clear":
    print("HIGH POLLEN CONDITIONS")
    print("Allergy sufferers may experience symptoms.")
    print("Consider antihistamines or limiting outdoor exposure.")

elif temperature >= 60 and humidity <= 70 and wind_speed <= 10:
    print("MODERATE POLLEN CONDITIONS")
    print("Some allergy symptoms possible.")

###Driving Conditions###

if condition == "Rain" or condition == "Snow" or condition == "Fog":
    print("DRIVING CAUTION")
    print("Allow extra stopping distance.")

###Tomorrow Conditions###

if tomorrow_temp <= 32:
    print("FREEZE EXPECTED TOMORROW")
    print("Protect pipes, cover plants, bring pets inside.")

elif tomorrow_rain > 5:
    print("HEAVY RAIN EXPECTED TOMORROW")
    print("Plan travel carefully and watch for flooding.")

elif tomorrow_temp >= 95:
    print("EXTREME HEAT EXPECTED TOMORROW")
    print("Hydrate and avoid long sun exposure.")
