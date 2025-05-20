Scanalyze Backend
Backend service for Scanalyze - an application for cosmetics ingredient analysis and skin profile management.

Overview
Scanalyze Backend provides REST API services for the Scanalyze Flutter application. It handles user authentication, profile management, and cosmetic product analysis.

Features
User Authentication: Secure JWT-based authentication
User Profile Management: Store and retrieve detailed skin profiles
Cosmetic Analysis: Analyze cosmetic products based on their ingredients
Technologies
FastAPI: High-performance Python web framework
MongoDB: NoSQL database for data storage
PyJWT: JSON Web Token implementation for authentication
Motor: Asynchronous MongoDB driver
Pydantic: Data validation and settings management
Docker/Docker Compose: Containerization for easy deployment
Getting Started
Prerequisites
Docker and Docker Compose
Python 3.11+ (for local development)
Installation
Clone the repository:

Create a .env file with the following variables:

Start the application with Docker Compose:

The API will be available at http://localhost:9091.

Local Development Setup
Create a virtual environment:

Install dependencies:

Set environment variables:

Run the server:

API Endpoints
Authentication
POST /login: Authenticate user and get JWT token
User Profile
GET /user/profile: Get current user profile
POST /user/profile: Update user profile
User Profile Schema
The user profile stores detailed information about skin characteristics, conditions, and lifestyle factors:

Testing
Run tests with pytest:

Or test specific modules:

Frontend Integration
This backend is designed to work with the Scanalyze Flutter application, which provides a user-friendly interface for:

User registration and authentication
Detailed skin profile creation
Product scanning and ingredient analysis
Personalized product recommendations
The frontend communicates with this backend through REST API endpoints.