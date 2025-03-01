![Cover](static/background.jpg)

# MFA Playground

A playground for tutorial about Multi-Factor Authentication (MFA).  
The project includes both Time-based One-Time Password (TOTP) and One-Time Password (OTP)
MFA implementations.

## Features

- User Sign Up and Sign In
- TOTP MFA using Google Authenticator or similar apps
- OTP MFA via email

## Requirements

- UV
- Docker (optional, for containerized deployment)

## Installation

### Local

1. Clone the repository:
   ```sh
   git clone https://github.com/sergeykuzmich/mfa-playground.git
   cd mfa-playground
   ```

2. Install the dependencies:
   ```sh
   uv sync
   ```

3. Run the application:
   ```sh
   uv run fastapi dev main.py
   ```

### Docker Deployment

1. Build the Docker image:
   ```sh
   docker build -t mfa-playground .
   ```

2. Run the Docker container:
   ```sh
   docker run -p 8000:8000 -v $(pwd):/application -v /application/.venv mfa-playground
   ```

## Usage

Access the application at [http://localhost:8000](http://localhost:8000).
