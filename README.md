# Airport Management System

Project Overview

    Airport Management System is a professional web-based system for managing all aspects 
    of air transportation. The system provides full functionality from basic infrastructure 
    management (countries, cities, airports) to complex business processes 
    (ticket booking, flight management, crew control).

# Key Features

    Automatic geocoding of cities using Nominatim API
    Automatic calculation of distances between airports
    Intelligent booking system with real-time seat validation
    Optimized queries to solve N+1 problems
    Multi-level access control with JWT authentication
    Advanced filtering and pagination for all resources

# Functionalities
Infrastructure Management

    Countries: Create and manage countries with currencies and time zones
    Cities: Automatic geocoding and saving coordinates
    Airports: Airport management with city binding
    Terminals and gates: Detailed management of airport infrastructure

Fleet Management

    Airlines: Airline profiles with logos and metadata
    Aircraft types: Aircraft catalog with characteristics
    Aircraft: Fleet management with cabin configuration

Operational management

    Routes: Automatic calculation of distances between airports
    Flights: Full schedule management with status control
    Crews: Flight assignment
    Booking: Ticketing system with validation

# Backend

    Django 5.2.4 
    Django REST Framework
    PostgreSQL 16.0 
    JWT - Authentication (180 minutes access, 1 day refresh token)
    Rate Limiting - 100 requests/day for anonymous users, 300/day for users

# Geospatial services

    GeoPy - Geocoding and distance calculation
    Nominatim - OpenStreetMap geocoding service

# DevOps

    Docker - Контейнеризація
    Docker Compose - Orchestration
    Alpine Linux - Легковажний базовий образ

# Documentation
http://127.0.0.1:8000/api/doc/swagger/#/airport/airport_terminals_list

    drf-spectacular - OpenAPI/Swagger documentation 
    Debug Toolbar - Development tools (only in DEBUG mode)

# Airport API
API service for airport management written on DRF

# API Ендпоінти

    Basic resources
GET/POST    /api/countries/         
GET/POST    /api/cities/        
GET/POST    /api/airlines/        
GET/POST    /api/airports/        
GET/POST    /api/airplane-types/ 
GET/POST    /api/airplanes/       
GET/POST    /api/terminals/     
GET/POST    /api/gates/            
GET/POST    /api/routes/          
GET/POST    /api/flights/    
GET/POST    /api/crews/       
GET/POST    /api/orders/     

    Special endpoints
POST /api/airlines/{id}/upload-image/       
POST /api/airplane-types/{id}/upload-image/  
GET  /api/flights/?departure=Kiev&arrival=  
GET  /api/crews/?flights=1,2,3        

    Authentication
POST /api/auth/register/  
POST /api/auth/token/       
POST /api/auth/refresh/   
GET  /api/auth/me/          

# Installing using GitHub

Install PostgreSQL and create db

    git clone https://github.com/AndriiRuhlyuk/airport-api-service.git
    cd airport-api
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    set DB_HOST=<your db hostname>
    set DB_NAME=<your db name>
    set DB_USER=<your db username>
    set DB_PASSWORD=<your db user password>
    set SECRET_KEY=<your secret key>
    python manage.py migrate
    python manage.py geocode_cities
    python manage.py runserver

# Run with docker

Docker should be installed

    docker-compose build
    docker-compose up

# Getting access

    create user via /api/user/register/
    get access token via /api/user/token/

# You can use following superuser (or create another one by yourself):
superuser cred.:

    Email: admin@admin.com
    Password.: super2025user

user1 cred.:

    Email: user@user.com
    Password.: qwert12345

user2 cred.:

    Email: user1@user1.com
    Password: qwerty123456

# Features

    JWT authenticated
    Admin panel /admin/
    Documentation is located at /api/schema/swagger/
    Managing airports, airlines, and airplanes
    Creating flights with routes and automatic distance calculation
    Booking tickets with seat validation
    Managing flight crews
    Automatic geocoding for cities
    Filtering flights, airports, and other entities
    Upload images for airlines and airplane types

# DB-structure:
[diagram](https://drive.google.com/file/d/1UuFeLkHRUa-sjs0EkaRc1vUEJ0jKJxuB/view?usp=sharing):
![drawAirPort.png](images/drawAirPort.png)
