# CarVal v2 - UAE Car Price Prediction API

A FastAPI-based machine learning service that predicts used car prices in the UAE market using a deep learning model trained on local market data.

## Features

- **Price Prediction**: Predict car prices based on vehicle specifications
- **Market-Specific**: Trained on UAE car market data
- **Real-time Inference**: Fast API responses with TensorFlow/Keras model
- **Model Management**: Hot-reload capability for model updates
- **Health Monitoring**: Built-in health checks and metrics endpoints

## Quick Start

### Prerequisites

- Python 3.8+
- Hugging Face account and repository with trained model

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd CarVal_v2
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Environment Variables

Create a `.env` file with the following variables:

```env
HF_REPO_ID=your-huggingface-repo-id
RELOAD_TOKEN=your-secret-reload-token
```

### Running the API

```bash
uvicorn api.api:app --reload --host 0.0.0.0 --port 8000
```

**Production API**: https://adw01-carval-api.hf.space/

**Local Development**: `http://localhost:8000`

## API Documentation

### Base URL

**Production**: `https://adw01-carval-api.hf.space/`

**Local Development**: `http://localhost:8000`

### Endpoints

#### 1. Health Check
**GET** `/health`

Returns the current status of the API and model.

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true,
  "trained_at": "2024-01-15T10:30:00Z"
}
```

#### 2. Predict Car Price
**POST** `/predict`

Predict the price of a used car based on its specifications.

**Request Body:**
```json
{
  "manufacturer": "Toyota",
  "model": "Camry",
  "year": 2020,
  "mileage": 50000,
  "fuel_type": "Petrol",
  "transmission": "Automatic",
  "body_type": "Sedan",
  "cylinder": 4,
  "seats": 5
}
```

**Response:**
```json
{
  "predicted_price_aed": 85000.00,
  "price_range_low": 82000.00,
  "price_range_high": 88000.00
}
```

**Field Descriptions:**
- `manufacturer`: Car manufacturer (e.g., "Toyota", "BMW", "Mercedes-Benz")
- `model`: Car model (e.g., "Camry", "X5", "C-Class")
- `year`: Manufacturing year (1990-2026)
- `mileage`: Total mileage in kilometers (>= 0)
- `fuel_type`: Fuel type ("Petrol", "Diesel", "Hybrid", "Electric")
- `transmission`: Transmission type ("Automatic", "Manual", "CVT")
- `body_type`: Body style ("Sedan", "SUV", "Coupe", "Hatchback", "Truck")
- `cylinder`: Number of cylinders (2-16, default: 4)
- `seats`: Number of seats (2-9, default: 5)

#### 3. Model Metrics
**GET** `/metrics`

Returns training metrics and model performance history.

**Response:**
```json
{
  "runs": [
    {
      "trained_at": "2024-01-15T10:30:00Z",
      "mae": 3000.50,
      "rmse": 4500.75,
      "r2_score": 0.92
    }
  ]
}
```

#### 4. Reload Model
**POST** `/reload-model`

Hot-reload the model from Hugging Face (requires authentication).

**Request Body:**
```json
{
  "token": "your-reload-token"
}
```

**Response:**
```json
{
  "status": "reloaded",
  "trained_at": "2024-01-15T10:30:00Z"
}
```

## Model Information

The API uses a TensorFlow/Keras neural network model trained on UAE car market data. The model considers:

- **Basic Features**: Manufacturer, model, year, mileage
- **Technical Specs**: Fuel type, transmission, body type, cylinders, seats
- **Derived Features**: Vehicle age, mileage per year, luxury brand detection
- **Binary Features**: Automatic transmission, SUV type, diesel fuel, luxury brand

### Performance Metrics

- **Mean Absolute Error (MAE)**: ~AED 3,000
- **R² Score**: ~0.92
- **Training Data**: UAE market listings (2020-2024)

## Architecture

```
CarVal_v2/
|
|--- api/
|    |--- api.py              # FastAPI application
|
|--- scraper/
|    |--- scrape.py           # Web scraping utilities
|
|--- ml/                      # Machine learning utilities (empty)
|--- train/                   # Training scripts
|
|--- requirements.txt         # Python dependencies
|--- .env                     # Environment variables
|--- .gitignore              # Git ignore rules
```

## Technology Stack

- **API Framework**: FastAPI 0.110.0
- **Machine Learning**: TensorFlow 2.16.1, scikit-learn 1.6.1
- **Data Processing**: pandas 2.2.0, numpy 1.26.4
- **Model Storage**: Hugging Face Hub
- **Web Server**: Uvicorn
- **Validation**: Pydantic 2.6.1

## Development

### Running Tests

```bash
# Add test commands when available
pytest tests/
```

### Model Training

```bash
python train/train.py
```

### Data Scraping

```bash
python scraper/scrape.py
```

## Deployment

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t carval-api .
docker run -p 8000:8000 carval-api
```

### Environment-Specific Configuration

- **Development**: Use `--reload` flag with uvicorn
- **Production**: Use a production WSGI server like Gunicorn
- **Cloud**: Compatible with AWS Lambda, Google Cloud Functions, Azure Functions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs` endpoint
- Review the health status at `/health` endpoint

## Roadmap

- [ ] Add support for more car features
- [ ] Implement model versioning
- [ ] Add confidence intervals
- [ ] Expand to other GCC markets
- [ ] Add image-based car condition assessment
