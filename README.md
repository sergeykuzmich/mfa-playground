# 🧨🧨🧨 #

## Important Notice ##
This repository contains a dummy application demonstrating various Multi-Factor Authentication (MFA) methods. It has not been developed with robust security practices or industry best practices and is intended solely for educational and testing purposes. It stores passwords in plain text in the database!!!

### Do Not Use It Anywhere, Especially in Production ###
- This code is **not secure** and may contain vulnerabilities.
- It is provided as-is, without warranties or guarantees of any kind.
- Do not deploy this application in any production environment or use it for managing sensitive data.

By using this repository, you acknowledge that you understand the limitations and risks involved. For any real-world implementation of MFA, please rely on well-vetted solutions and consult with security experts.

# 🧨🧨🧨 #

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
