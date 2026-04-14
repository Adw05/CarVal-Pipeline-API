# CarVal API Documentation

## Overview

The CarVal API provides machine learning-powered car price predictions specifically trained for the UAE market. This RESTful API uses FastAPI and TensorFlow to deliver real-time price predictions based on vehicle specifications.

## Base URL

**Production**: `https://adw01-carval-api.hf.space/`

For local development:
```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication for prediction endpoints. However, the model reload endpoint requires a secret token.

## Rate Limiting

No rate limiting is currently implemented, but it's recommended for production deployments.

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Successful request
- `400 Bad Request`: Invalid input data
- `403 Forbidden`: Invalid reload token
- `503 Service Unavailable`: Model not loaded

## Endpoints

### 1. Health Check

**Endpoint**: `GET /health`

**Description**: Check the API status and model availability.

**Parameters**: None

**Response**:
```json
{
  "status": "ok",
  "model_loaded": true,
  "trained_at": "2024-01-15T10:30:00Z"
}
```

**Response Fields**:
- `status` (string): API health status
- `model_loaded` (boolean): Whether the ML model is loaded
- `trained_at` (string): Timestamp of last model training

---

### 2. Predict Car Price

**Endpoint**: `POST /predict`

**Description**: Predict the market price of a used car in the UAE.

**Request Body**:
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

**Request Parameters**:

| Parameter | Type | Required | Constraints | Example |
|-----------|------|----------|-------------|---------|
| manufacturer | string | Yes | Valid car manufacturer | "Toyota" |
| model | string | Yes | Car model name | "Camry" |
| year | integer | Yes | 1990-2026 | 2020 |
| mileage | integer | Yes | >= 0 | 50000 |
| fuel_type | string | Yes | "Petrol", "Diesel", "Hybrid", "Electric" | "Petrol" |
| transmission | string | Yes | "Automatic", "Manual", "CVT" | "Automatic" |
| body_type | string | Yes | "Sedan", "SUV", "Coupe", "Hatchback", "Truck" | "Sedan" |
| cylinder | integer | No | 2-16, default: 4 | 4 |
| seats | integer | No | 2-9, default: 5 | 5 |

**Response**:
```json
{
  "predicted_price_aed": 85000.00,
  "price_range_low": 82000.00,
  "price_range_high": 88000.00
}
```

**Response Fields**:
- `predicted_price_aed` (float): Predicted market price in AED
- `price_range_low` (float): Lower bound of price range (predicted - MAE)
- `price_range_high` (float): Upper bound of price range (predicted + MAE)

**Example Requests**:

**Luxury SUV**:
```json
{
  "manufacturer": "Mercedes-Benz",
  "model": "GLE 350",
  "year": 2021,
  "mileage": 35000,
  "fuel_type": "Petrol",
  "transmission": "Automatic",
  "body_type": "SUV",
  "cylinder": 6,
  "seats": 7
}
```

**Economy Sedan**:
```json
{
  "manufacturer": "Nissan",
  "model": "Sunny",
  "year": 2019,
  "mileage": 75000,
  "fuel_type": "Petrol",
  "transmission": "Automatic",
  "body_type": "Sedan",
  "cylinder": 4,
  "seats": 5
}
```

---

### 3. Model Metrics

**Endpoint**: `GET /metrics`

**Description**: Retrieve model performance metrics and training history.

**Parameters**: None

**Response**:
```json
{
  "runs": [
    {
      "trained_at": "2024-01-15T10:30:00Z",
      "mae": 3000.50,
      "rmse": 4500.75,
      "r2_score": 0.92,
      "training_samples": 15000,
      "validation_samples": 3000
    }
  ]
}
```

**Response Fields**:
- `runs` (array): Array of training runs
- `trained_at` (string): Training timestamp
- `mae` (float): Mean Absolute Error in AED
- `rmse` (float): Root Mean Square Error in AED
- `r2_score` (float): R-squared score (0-1)
- `training_samples` (integer): Number of training samples
- `validation_samples` (integer): Number of validation samples

---

### 4. Reload Model

**Endpoint**: `POST /reload-model`

**Description**: Hot-reload the latest model from Hugging Face Hub.

**Request Body**:
```json
{
  "token": "your-secret-reload-token"
}
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| token | string | Yes | Secret reload token (configured in environment) |

**Response**:
```json
{
  "status": "reloaded",
  "trained_at": "2024-01-15T10:30:00Z"
}
```

**Response Fields**:
- `status` (string): Reload operation status
- `trained_at` (string): Timestamp of newly loaded model

---

## Data Models

### CarInput Schema

```json
{
  "manufacturer": "string",
  "model": "string",
  "year": "integer",
  "mileage": "integer",
  "fuel_type": "string",
  "transmission": "string",
  "body_type": "string",
  "cylinder": "integer",
  "seats": "integer"
}
```

### PredictionResponse Schema

```json
{
  "predicted_price_aed": "number",
  "price_range_low": "number",
  "price_range_high": "number"
}
```

## Feature Engineering

The API automatically generates additional features from the input data:

- **age**: Vehicle age in years (current_year - year)
- **mileage_per_year**: Average annual mileage
- **is_automatic**: Binary flag for automatic transmission
- **is_suv**: Binary flag for SUV body type
- **is_diesel**: Binary flag for diesel fuel
- **is_luxury**: Binary flag for luxury brands (Mercedes-Benz, BMW, Audi, Lexus, Infiniti, Porsche, Jaguar, Land Rover)

## Supported Manufacturers

The model supports major manufacturers available in the UAE market:

**Popular Brands**: Toyota, Honda, Nissan, Mitsubishi, Hyundai, Kia, Mazda

**Luxury Brands**: Mercedes-Benz, BMW, Audi, Lexus, Infiniti, Porsche, Jaguar, Land Rover

**American Brands**: Ford, Chevrolet, GMC, Cadillac

**European Brands**: Volkswagen, Volvo, Peugeot, Renault

## Model Performance

### Accuracy Metrics

- **Mean Absolute Error**: ~AED 3,000
- **Root Mean Square Error**: ~AED 4,500
- **R² Score**: ~0.92

### Training Data

- **Source**: UAE car market listings (2020-2024)
- **Dataset Size**: ~18,000 vehicles
- **Coverage**: All major emirates
- **Price Range**: AED 15,000 - 500,000

### Limitations

- Model trained on data up to 2024
- May not account for recent market fluctuations
- Limited to commonly available models in UAE
- Does not consider vehicle condition or accident history

## Usage Examples

### Python Example

```python
import requests

# API endpoint
url = "http://localhost:8000/predict"

# Car data
car_data = {
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

# Make prediction
response = requests.post(url, json=car_data)
result = response.json()

print(f"Predicted Price: AED {result['predicted_price_aed']:,.2f}")
print(f"Price Range: AED {result['price_range_low']:,.2f} - AED {result['price_range_high']:,.2f}")
```

### JavaScript Example

```javascript
const apiUrl = 'http://localhost:8000/predict';

const carData = {
    manufacturer: "Toyota",
    model: "Camry",
    year: 2020,
    mileage: 50000,
    fuel_type: "Petrol",
    transmission: "Automatic",
    body_type: "Sedan",
    cylinder: 4,
    seats: 5
};

fetch(apiUrl, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(carData)
})
.then(response => response.json())
.then(data => {
    console.log(`Predicted Price: AED ${data.predicted_price_aed.toLocaleString()}`);
    console.log(`Price Range: AED ${data.price_range_low.toLocaleString()} - AED ${data.price_range_high.toLocaleString()}`);
})
.catch(error => console.error('Error:', error));
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "manufacturer": "Toyota",
       "model": "Camry",
       "year": 2020,
       "mileage": 50000,
       "fuel_type": "Petrol",
       "transmission": "Automatic",
       "body_type": "Sedan",
       "cylinder": 4,
       "seats": 5
     }'
```

## SDK and Client Libraries

Currently, no official SDK is available. However, the REST API can be easily integrated into any application using standard HTTP clients.

## Interactive Documentation

When running the API locally, you can access interactive documentation at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These interfaces provide:

- Interactive API testing
- Request/response schemas
- Parameter validation
- Example requests

## Monitoring and Logging

### Health Monitoring

- Use `/health` endpoint for uptime monitoring
- Monitor `model_loaded` field to ensure model availability
- Track `trained_at` timestamp for model updates

### Performance Monitoring

- Monitor response times for `/predict` endpoint
- Track prediction accuracy against actual market prices
- Log failed predictions for error analysis

## Troubleshooting

### Common Issues

**Model Not Loaded (503 Error)**:
- Check Hugging Face repository configuration
- Verify `HF_REPO_ID` environment variable
- Ensure model files exist in the repository

**Invalid Input (400 Error)**:
- Validate all required fields are present
- Check data types and constraints
- Ensure manufacturer and model names are spelled correctly

**Slow Response Times**:
- Check server resources (CPU, memory)
- Monitor model loading time
- Consider scaling horizontally for high traffic

### Debug Mode

Enable debug logging by setting:
```bash
export TF_CPP_MIN_LOG_LEVEL=0
```

## Version History

### v2.0.0 (Current)
- FastAPI implementation
- Hugging Face model integration
- Improved feature engineering
- Enhanced error handling

### v1.0.0 (Legacy)
- Basic Flask implementation
- Local model storage
- Limited feature set

## Support

For technical support:

1. Check the health endpoint: `GET /health`
2. Review API documentation at `/docs`
3. Verify environment configuration
4. Check model metrics at `/metrics`

## Roadmap

### Planned Features

- **Batch Prediction**: Predict prices for multiple cars
- **Image Analysis**: Assess car condition from photos
- **Market Trends**: Historical price trends and forecasts
- **Geographic Pricing**: Price variations by emirate
- **Custom Models**: Industry-specific pricing models

### API Improvements

- **Authentication**: API key-based access control
- **Rate Limiting**: Prevent abuse and ensure fair usage
- **Webhooks**: Real-time price alerts
- **GraphQL**: Alternative query interface
- **gRPC**: High-performance binary protocol
