# Report Builder Backend

This is the FastAPI backend for the AI-Led Collaborative Report Generator.

## Architecture

The backend follows a Planner → Executor → Reflector loop architecture and provides the following key endpoints:

1. Session creation
2. Session state management
3. Intake responses processing
4. Chat orchestration
5. Section saving
6. Chapter/full report downloads

## Technology Stack

- **Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **LLM Integration**: Anthropic Claude API
- **Memory Management**: In-memory context storage
- **Document Generation**: PDF/DOCX export capabilities

## Getting Started

1. Install dependencies:
   ```
   poetry install
   ```

2. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your API keys.

3. Run the development server:
   ```
   poetry run uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
