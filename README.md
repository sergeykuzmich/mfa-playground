![Cover](static/background.jpg)

# MFA Playground

A playground for a tutorial on Multi-Factor Authentication (MFA).  
The project includes implementations of both Time-based One-Time Password (TOTP) and One-Time Password (OTP) MFA methods.

## Features

- User Sign Up and Sign In
- TOTP MFA using Google Authenticator or similar apps
- OTP MFA via email

## Requirements

- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com)

## Prerequisites

- Python 3.13 or higher
- Docker 20.10.7 or higher
- Docker Compose 1.29.2 or higher

## Development

### Local

1. Clone the repository:
   ```sh
   git clone https://github.com/sergeykuzmich/mfa-playground.git
   cd mfa-playground
   ```

2. Copy the example environment file and provide valid configuration:
   ```sh
   cp .env.example .env
   ```

3. Install the dependencies:
   ```sh
   uv sync
   ```

4. Run the application:
   ```sh
   uv run fastapi dev main.py
   ```

### Docker Compose

1. Clone the repository:
   ```sh
   git clone https://github.com/sergeykuzmich/mfa-playground.git
   cd mfa-playground
   ```

2. Copy the example environment file and provide valid configuration:
   ```sh
   cp .env.example .env
   ```

3. Run the application:
   ```sh
   docker compose up
   ```

## Deployment

1. Build the Docker image:
   ```sh
   docker build -t mfa-playground .
   ```

2. Run the Docker container with mapped ports and env file:
   ```sh
   docker run -p 8000:8000 --env-file .env mfa-playground
   ```

## Usage

Access the application at [http://localhost:8000](http://localhost:8000).

## Troubleshooting

### Common Issues

1. **Docker: "Cannot connect to the Docker daemon"**
   - Ensure Docker is running on your machine.
   - Verify that your user has permission to access Docker.

2. **uv: "Command not found"**
   - Ensure `uv` is installed and available in your PATH.
