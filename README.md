# Scanalyze Backend

Backend service for Scanalyze - an application for cosmetics ingredient analysis and skin profile management.

---

## Overview

Scanalyze Backend provides REST API services for the Scanalyze Flutter application. It handles user authentication, profile management, and cosmetic product analysis.

---

## Features

- **User Authentication**: Secure JWT-based authentication  
- **User Profile Management**: Store and retrieve detailed skin profiles  
- **Cosmetic Analysis**: Analyze cosmetic products based on their ingredients

---

## Technologies

- **FastAPI** 
- **MongoDB**
- **MySQL**
- **PyJWT** 
- **Motor**
- **Pydantic**
- **Docker/Docker Compose**
- **ToxValDB**: EPA's toxicology database for ingredient analysis

---

## Data Resources

### ToxValDB Database

The application uses the EPA's ToxValDB database for ingredient analysis and toxicology data:

- **Source**: [EPA ToxValDB](https://cfpub.epa.gov/si/si_public_record_report.cfm?dirEntryId=344315&Lab=NCCT)
- **Local Setup**: For development, you'll need to download the ToxValDB database locally
- **Docker Integration**: The application uses a dump of this database in the Docker container

#### Downloading ToxValDB

1. Visit the [EPA ToxValDB page](https://cfpub.epa.gov/si/si_public_record_report.cfm?dirEntryId=344315&Lab=NCCT)
2. Download the database files following the EPA's instructions
3. Place the downloaded database files in the `data/toxvaldb` directory


## Getting Started

### Prerequisites

- Docker and Docker Compose  
- Python 3.11+ (for local development)
- ToxValDB database files (see [Data Resources](#data-resources) section)

### Installation

1. Clone the repository:

   ```bash
   git clone [repository-url]
   cd scanalyze_backend
   ```

2. Create a `.env` file with the following variables:

   ```env
   JWT_SECRET_KEY=your_secret_key_here
   MONGO_URI=mongodb://mongo:27055
   ```

3. Start the application with Docker Compose:

   ```bash
   docker-compose up -d
   ```

The API will be available at `http://localhost:9091`.

---

## Local Development Setup

1. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:

   ```bash
   export JWT_SECRET_KEY=your_secret_key_here
   export MONGO_URI=mongodb://localhost:27055
   ```

4. Run the server:

   ```bash
   uvicorn main:app --reload
   ```

---

## API Endpoints

### Authentication

- `POST /login`: Authenticate user and get JWT token

### User Profile

- `GET /user/profile`: Get current user profile  
- `POST /user/profile`: Update user profile

---

## User Profile Schema

The user profile stores detailed information about skin characteristics, conditions, and lifestyle factors:

```json
{
  "age": 30,
  "gender": "Female",
  "weight": 65.0,
  "height": 170.0,
  "skinType": "Dry",
  "sensitiveSkin": true,
  "atopicSkin": false,
  "acneProne": false,
  "hasAllergies": true,
  "cosmeticAllergies": ["Fragrances", "Preservatives"],
  "generalAllergies": ["Pollen"],
  "acneVulgaris": false,
  "psoriasis": false,
  "eczema": true,
  "rosacea": false,
  "photosensitizingDrugs": false,
  "diuretics": false,
  "otherMedications": "None",
  "medicalProcedures": "None",
  "smoking": "Never",
  "stressLevel": 7,
  "tanning": "Rarely",
  "pregnancy": false
}
```

---

## Testing

Run tests with pytest:

```bash
python -m pytest
```

Or test specific modules:

```bash
python -m pytest tests/routes/test_user_profile.py -v
```

---

## Frontend Integration

This backend is designed to work with the Scanalyze Flutter application, which provides a user-friendly interface for:

- User registration and authentication  
- Detailed skin profile creation  
- Product scanning and ingredient analysis  
- Personalized product recommendations

The frontend communicates with this backend through REST API endpoints.
