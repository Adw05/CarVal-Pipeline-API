import os, json, joblib
import numpy as np
import pandas as pd
import psycopg2
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime
from huggingface_hub import HfApi, login, hf_hub_download
from dotenv import load_dotenv

load_dotenv()

DB_URL   = os.getenv("SUPABASE_DB_URL")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_REPO  = os.getenv("HF_REPO_ID")

MODEL_PATH   = "car_price_predictor.h5" 
PREPROCESSOR = "preprocessor.pkl"
METRICS_PATH = "metrics.json"

LUXURY_BRANDS = [
    'Mercedes-Benz', 'BMW', 'Audi', 'Lexus',
    'Infiniti', 'Porsche', 'Jaguar', 'Land Rover'
]

def load_data() -> pd.DataFrame:
    print("Loading new data and replay buffer from Supabase...")
    conn = psycopg2.connect(DB_URL)
    query = """
        (SELECT manufacturer, model, year, price, mileage,
                fuel_type, transmission, body_type, seats, cylinder
         FROM car_listings_raw
         WHERE price > 0 
           AND scraped_at >= NOW() - INTERVAL '14 days')
        UNION ALL
        (SELECT manufacturer, model, year, price, mileage,
                fuel_type, transmission, body_type, seats, cylinder
         FROM car_listings_raw
         WHERE price > 0 
           AND scraped_at < NOW() - INTERVAL '14 days'
         ORDER BY RANDOM()
         LIMIT 1000)
    """
    df = pd.read_sql(query, conn)
    conn.close()
    print(f"  Loaded {len(df):,} rows.")
    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    q1  = df['price'].quantile(0.01)
    q99 = df['price'].quantile(0.99)
    return df[(df['price'] >= q1) & (df['price'] <= q99)].copy()

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    current_year = pd.Timestamp.now().year
    df['age']              = current_year - df['year']
    df['mileage_per_year'] = df['mileage'] / (df['age'] + 1)
    df['is_automatic']     = (df['transmission'] == 'Automatic').astype(int)
    df['is_suv']           = df['body_type'].apply(lambda x: 1 if 'SUV' in str(x) else 0)
    df['is_diesel']        = df['fuel_type'].apply(lambda x: 1 if 'Diesel' in str(x) else 0)
    df['is_luxury']        = df['manufacturer'].apply(lambda x: 1 if x in LUXURY_BRANDS else 0)
    return df

def finetune(df: pd.DataFrame):
    df = clean_data(df)
    df = engineer_features(df)
    X = df.drop('price', axis=1)
    y = df['price']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    prep_path    = hf_hub_download(repo_id=HF_REPO, filename=PREPROCESSOR)
    preprocessor = joblib.load(prep_path)
    X_train_pp   = preprocessor.transform(X_train)
    X_test_pp    = preprocessor.transform(X_test)

    model_path = hf_hub_download(repo_id=HF_REPO, filename=MODEL_PATH)
    
    class PatchedDense(keras.layers.Dense):
        @classmethod
        def from_config(cls, config):
            config.pop("quantization_config", None)
            return super().from_config(config)

    with keras.utils.custom_object_scope({'Dense': PatchedDense}):
        model = keras.models.load_model(model_path)

    model.compile(
        loss='mean_absolute_error',
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        metrics=['mae', 'mse'],
    )

    early_stopping = keras.callbacks.EarlyStopping(
        patience=5, min_delta=0.001, restore_best_weights=True,
    )

    model.fit(
        X_train_pp, y_train,
        validation_data=(X_test_pp, y_test),
        batch_size=32, epochs=20, callbacks=[early_stopping], verbose=1,
    )

    y_pred = model.predict(X_test_pp).flatten()
    mae, r2 = mean_absolute_error(y_test, y_pred), r2_score(y_test, y_pred)
    
    metrics = {
        "mae": round(float(mae), 2), 
        "r2": round(float(r2), 4),
        "train_rows": int(len(X_train)), 
        "test_rows": int(len(X_test)),
        "trained_at": datetime.utcnow().isoformat(),
    }
    return model, preprocessor, metrics

def push_to_hf(model, preprocessor, metrics):
    login(token=HF_TOKEN)
    api = HfApi()

    #MODEL VALIDATION GATE
    try:
        existing_path = hf_hub_download(repo_id=HF_REPO, filename=METRICS_PATH)
        with open(existing_path) as f: history = json.load(f)
        
        # Get the previous best MAE (lower is better)
        if "runs" in history and len(history["runs"]) > 0:
            previous_mae = history["runs"][-1]["mae"]
            print(f"Comparing performance: New MAE {metrics['mae']} vs Previous MAE {previous_mae}")
            
            # Threshold: Allow a 5% margin for data noise, or strict better only
            if metrics['mae'] > (previous_mae * 1.05):
                print(f"REJECTED: New model performance is significantly worse. Keeping old model.")
                return False
        
        if "runs" not in history: history = {"runs": [history]}
    except Exception as e:
        print(f"No existing metrics found or error: {e}. Starting fresh history.")
        history = {"runs": []}

    #UPLOAD SECTION
    metrics["week"] = len(history["runs"]) + 1
    history["runs"].append(metrics)

    model.save(MODEL_PATH)
    joblib.dump(preprocessor, PREPROCESSOR)
    with open(METRICS_PATH, "w") as f: json.dump(history, f, indent=2)

    for fname in [MODEL_PATH, PREPROCESSOR, METRICS_PATH]:
        api.upload_file(path_or_fileobj=fname, path_in_repo=fname, repo_id=HF_REPO, repo_type="model")
        print(f"  ✓ {fname} updated in {HF_REPO}")
    return True

if __name__ == "__main__":
    df = load_data()
    if len(df) < 1050: 
        print("Not enough new data this week. Skipping.")
        exit(0)

    model, preprocessor, metrics = finetune(df)
    success = push_to_hf(model, preprocessor, metrics)
    
    if success:
        print("\nFine-tune complete and pushed.")
    else:
        print("\nFine-tune complete but rejected by performance gate.")