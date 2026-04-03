import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI(title="CityPulse V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    message: str
    city: str


class CityRequest(BaseModel):
    city: str


@app.get("/api/weather")
async def get_weather(city: str):
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_KEY,
            "units": "metric"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params)
            data = r.json()
        if data.get("cod") != 200:
            return {"error": "City not found"}
        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "description": data["weather"][0]["description"].title(),
            "icon": data["weather"][0]["icon"],
            "lat": data["coord"]["lat"],
            "lon": data["coord"]["lon"],
            "visibility": data.get("visibility", 0) // 1000,
            "pressure": data["main"]["pressure"]
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/forecast")
async def get_forecast(city: str):
    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": OPENWEATHER_KEY,
            "units": "metric",
            "cnt": 5
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params)
            data = r.json()
        forecasts = []
        for item in data.get("list", []):
            forecasts.append({
                "time": item["dt_txt"],
                "temp": round(item["main"]["temp"]),
                "description": item["weather"][0]["description"].title(),
                "icon": item["weather"][0]["icon"],
                "humidity": item["main"]["humidity"],
                "wind": item["wind"]["speed"]
            })
        return {"forecasts": forecasts}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/places")
async def get_places(city: str):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city.replace(' ', '_').title()}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            data = r.json()
        summary = data.get("extract", "")[:800]
        return {
            "city": city,
            "summary": summary,
            "thumbnail": data.get("thumbnail", {}).get("source", "")
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/country")
async def get_country(code: str):
    try:
        url = f"https://restcountries.com/v3.1/alpha/{code}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            data = r.json()[0]
        return {
            "name": data["name"]["common"],
            "capital": data.get("capital", [""])[0],
            "population": f"{data.get('population', 0):,}",
            "languages": list(data.get("languages", {}).values())[:3],
            "currencies": [v["name"] for v in data.get("currencies", {}).values()],
            "flag": data.get("flags", {}).get("png", ""),
            "region": data.get("region", "")
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/chat")
async def chat(body: ChatMessage):
    try:
        prompt = f"""You are CityPulse AI assistant, an expert travel and city guide.
The user is asking about {body.city}.
User message: {body.message}
Give a helpful, concise and enthusiastic response about {body.city}.
Include relevant facts, tips, and recommendations.
Keep response under 150 words."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": "Bearer " + str(GROQ_KEY),
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200
                }
            )
            data = r.json()
            if "choices" in data:
                return {"response": data["choices"][0]["message"]["content"]}
            return {"response": "Sorry, I could not process that request."}
    except Exception as e:
        return {"response": "Error: " + str(e)}


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.get("/about")
async def about():
    return FileResponse("frontend/pages/about.html")


@app.get("/contact")
async def contact():
    return FileResponse("frontend/pages/contact.html")
