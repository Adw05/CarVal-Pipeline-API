import os, json, joblib
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from huggingface_hub import hf_hub_download
from tensorflow import keras
from dotenv import load_dotenv

load_dotenv()

HF_REPO = os.getenv("HF_REPO_ID")

LUXURY_BRANDS = [
    'Mercedes-Benz', 'BMW', 'Audi', 'Lexus',
    'Infiniti', 'Porsche', 'Jaguar', 'Land Rover'
]

state: dict = {"model": None, "preprocessor": None, "metrics": None}

def load_from_hf():
    print("Downloading model from Hugging Face...")
    # Loading the clean .keras model
    model_path = hf_hub_download(repo_id=HF_REPO, filename="car_price_predictor.h5")
    prep_path  = hf_hub_download(repo_id=HF_REPO, filename="preprocessor.pkl")
    meta_path  = hf_hub_download(repo_id=HF_REPO, filename="metrics.json")

    class PatchedDense(keras.layers.Dense):
        @classmethod
        def from_config(cls, config):
            config.pop("quantization_config", None)
            return super().from_config(config)

    with keras.utils.custom_object_scope({'Dense': PatchedDense}):
        state["model"] = keras.models.load_model(model_path)
    state["preprocessor"] = joblib.load(prep_path)
    with open(meta_path) as f:
        state["metrics"] = json.load(f)

    last_run = state["metrics"]["runs"][-1]
    print(f"  Model loaded — trained at {last_run['trained_at']}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_from_hf()
    yield

app = FastAPI(
    title="CarVal — UAE Car Price API",
    description="Predicts used car prices in the UAE market.",
    version="2.0.0",
    lifespan=lifespan,
)

class CarInput(BaseModel):
    manufacturer: str = Field(..., example="Toyota")
    model:        str = Field(..., example="Camry")
    year:         int = Field(..., ge=1990, le=2026, example=2020)
    mileage:      int = Field(..., ge=0, example=50000)
    fuel_type:    str = Field(..., example="Petrol")
    transmission: str = Field(..., example="Automatic")
    body_type:    str = Field(..., example="Sedan")
    cylinder:     int = Field(4, ge=2, le=16, example=4)
    seats:        int = Field(5, ge=2, le=9, example=5)

def prepare(car: CarInput) -> pd.DataFrame:
    current_year = pd.Timestamp.now().year
    age = current_year - car.year

    return pd.DataFrame([{
        "manufacturer":     car.manufacturer,
        "model":            car.model,
        "year":             car.year,
        "mileage":          car.mileage,
        "fuel_type":        car.fuel_type,
        "transmission":     car.transmission,
        "body_type":        car.body_type,
        "cylinder":         car.cylinder,
        "seats":            car.seats,
        "age":              age,
        "mileage_per_year": car.mileage / (age + 1),
        "is_automatic":     int(car.transmission == "Automatic"),
        "is_suv":           int("SUV" in car.body_type),
        "is_diesel":        int("Diesel" in car.fuel_type),
        "is_luxury":        int(car.manufacturer in LUXURY_BRANDS),
    }])

@app.get("/health")
def health():
    last_run = state["metrics"]["runs"][-1] if state["metrics"] else None
    return {
        "status": "ok",
        "model_loaded": state["model"] is not None,
        "trained_at": last_run["trained_at"] if last_run else None,
    }

@app.post("/predict", response_model=dict)
def predict(car: CarInput):
    if state["model"] is None:
        raise HTTPException(503, "Model not loaded yet")
    try:
        df    = prepare(car)
        X_pp  = state["preprocessor"].transform(df)
        price = float(state["model"].predict(X_pp)[0][0])
        
        # FIX: Access mae from the latest run in the metrics history
        last_run = state["metrics"]["runs"][-1]
        mae      = last_run["mae"]

        return {
            "predicted_price_aed": round(price, 2),
            "price_range_low":     round(max(0, price - mae), 2),
            "price_range_high":    round(price + mae, 2),
        }
    except Exception as e:
        raise HTTPException(400, f"Prediction failed: {e}")

@app.get("/metrics")
def metrics_history():
    if not state["metrics"]:
        raise HTTPException(503, "Metrics not loaded")
    return state["metrics"]

@app.post("/reload-model")
def reload_model(token: str):
    if token != os.getenv("RELOAD_TOKEN", "changeme"):
        raise HTTPException(403, "Invalid token")
    load_from_hf()
    return {"status": "reloaded", "trained_at": state["metrics"]["trained_at"]}