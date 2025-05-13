# Complete Installation Guide for DataFlow AI

This guide details the various methods of installing and configuring DataFlow AI. Choose the one that best suits your needs.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation with Docker (recommended)](#installation-with-docker-recommended)
- [Manual Installation](#manual-installation)
- [Configuring Outlines for Structured Extraction](#configuring-outlines-for-structured-extraction)
- [OpenAI API Configuration](#openai-api-configuration)
- [Frontend Configuration](#frontend-configuration)
- [Installation Verification](#installation-verification)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)

## Prerequisites

### Minimum Requirements
- Operating System: Linux, macOS, or Windows
- CPU: 2 cores, 4 GB RAM (minimum)
- Disk Space: 1 GB for installation, plus space for processed files

### Required Software
- Docker and Docker Compose (for Docker installation)
- **Python 3.12** specifically (for manual installation)
- Node.js 14+ (for manual frontend installation)
- Git

> ⚠️ **IMPORTANT**: DataFlow AI requires **Python 3.12** specifically due to dependency with the Outlines 0.2.3 library. Earlier or newer versions of Python may not work correctly.

## Installation with Docker (recommended)

Installation with Docker is the simplest method and ensures a consistent environment.

### 1. Clone the Repository

```bash
git clone https://github.com/stranxik/dataflow-ai.git
cd dataflow-ai
```

### 2. Configure Environment Variables

```bash
# Copy the example files
cp .env.example .env
cp frontend/.env.example frontend/.env

# Edit the files according to your needs
nano .env  # or use your preferred editor
nano frontend/.env
```

Important variables to configure in `.env`:
```
API_KEY=your_secure_api_key
OPENAI_API_KEY=your_openai_api_key
```

Important variables to configure in `frontend/.env`:
```
VITE_API_KEY=your_secure_api_key  # Must match API_KEY in .env
```

### 3. Build and Start Services

```bash
docker-compose up -d
```

This will start:
- The backend API on http://localhost:8000
- The frontend interface on http://localhost:80
- Containers for CLI and other services

### 4. Verify Installation

```bash
# Check that containers are running
docker-compose ps

# Test the CLI
docker-compose run cli test
```

## Manual Installation

Manual installation offers more control and is recommended for development environments.

### 1. Clone the Repository

```bash
git clone https://github.com/stranxik/dataflow-ai.git
cd dataflow-ai
```

### 2. Configure Backend Environment

```bash
# Create a Python 3.12 virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env according to your needs
```

### 3. Configure Frontend

```bash
cd frontend

# Install Node.js dependencies
npm install

# Configure environment variables
cp .env.example .env
# Edit .env according to your needs
```

### 4. Start Services

In a first terminal (backend):
```bash
# At the root of the project, with the virtual environment activated
python run_api.py
```

In a second terminal (frontend):
```bash
cd frontend
npm run dev
```

## Configuring Outlines for Structured Extraction

DataFlow AI uses the [Outlines](https://github.com/dottxt/outlines) library for structured extraction from LLMs.

### Specific Outlines Requirements

**IMPORTANT**: Outlines 0.2.3 requires **Python 3.12** specifically. For this reason, it is recommended to create a dedicated virtual environment:

```bash
# Create a virtual environment with Python 3.12
python3.12 -m venv venv_outlines

# Activate the environment
source venv_outlines/bin/activate  # Linux/Mac
venv_outlines\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

Newer Python versions (3.13+) are not compatible with Outlines 0.2.3.

### Outlines Operating Modes

Two operating modes are available:

1. **Full Mode**: With the Outlines library installed and an OpenAI API key
2. **Degraded Mode**: Operation without Outlines or without an API key (some features disabled)

The system automatically detects the available configuration and adapts accordingly.

## OpenAI API Configuration

For LLM enrichment and image analysis features, an OpenAI API key is required.

### 1. Obtain an API Key

1. Create an account on [OpenAI Platform](https://platform.openai.com/)
2. Access the API Keys section
3. Create a new API key

### 2. Configure the Key in DataFlow AI

Add your API key in the `.env` file:

```
OPENAI_API_KEY=your_openai_api_key
```

### 3. Models Used

DataFlow AI uses different models depending on the features:
- `gpt-4.1` for image analysis in PDFs
- `gpt-4-turbo` for JSON data enrichment
- `gpt-3.5-turbo` as a fallback for some less complex tasks

## Frontend Configuration

The frontend offers a modern user interface to access DataFlow AI's features.

### Configuration Options

In the `frontend/.env` file:

```
# API key to connect to the backend
VITE_API_KEY=your_secure_api_key

# API URL (default: /api)
VITE_API_URL=/api

# File limitations
VITE_MAX_PDF_SIZE_MB=50
VITE_DEFAULT_IMAGES_ANALYSIS=10
```

## Installation Verification

To verify that all components are working correctly:

### 1. Test the API

```bash
curl http://localhost:8000/api/pdf/test -H "X-API-Key: your_secure_api_key"
```

You should receive a JSON response indicating that the API is working.

### 2. Verify Outlines Integration

```bash
python -m tests.test_outlines_integration
```

### 3. Test the CLI

```bash
python -m cli.cli test
```

## Troubleshooting Common Issues

### API Won't Start

- Check that port 8000 is not already in use
- Verify that all dependencies are installed
- Check the logs: `docker-compose logs api`

### Authentication Errors

- Verify that the same API key is configured in `.env` and `frontend/.env`
- Make sure requests include the `X-API-Key` header

### Issues with Outlines

- Verify you are using Python 3.12 specifically
- If installation fails, try: `pip install outlines==0.2.3`

### PDF File Processing Errors

- Make sure the OpenAI API key is valid
- Check that the PDF file is not corrupted or protected

### Docker Issues

- Try rebuilding the images: `docker-compose build --no-cache`
- Check available disk space
- Check the logs: `docker-compose logs` 