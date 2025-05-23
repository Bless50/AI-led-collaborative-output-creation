# AI-Led Collaborative Report Generator

A tool that enables students to co-create academic reports via a structured, AI-driven Canvas interface, enforcing active learning.

## Features

- Upload institutional guide to structure the report
- AI-led section-by-section workflow
- Collaborative drafting with AI assistance
- Web search integration for citations
- Export to PDF/DOCX formats
- No user accounts required (session-based)

## Tech Stack

- **Frontend**: React + Vite, Tailwind CSS, shadcn/ui (for prebuilt components)
- **Backend**: FastAPI (Python)
- **LLM**: Anthropic Claude API
- **Database**: SQLite
- **Search**: Web-search integration with Tavily API

## Project Structure

```
report_builder/
├── backend/              # FastAPI backend
│   ├── app/              # Application code
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core functionality
│   │   ├── db/           # Database models and operations
│   │   ├── services/     # Services (Anthropic, Search, etc.)
│   │   └── utils/        # Utility functions
│   ├── alembic/          # Database migrations
│   ├── tests/            # Backend tests
│   ├── pyproject.toml    # Python dependencies
│   └── poetry.lock       # Locked dependencies
├── frontend/             # React frontend
│   ├── public/           # Static files
│   ├── src/              # Source code
│   │   ├── components/   # React components
│   │   ├── services/     # API services
│   │   ├── styles/       # CSS styles
│   │   └── utils/        # Utility functions
│   ├── package.json      # JavaScript dependencies
│   └── package-lock.json # Locked dependencies
└── README.md             # Project documentation
```

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- Anthropic API key
- Tavily API key

### Installation

1. Clone the repository
2. Set up the backend:
   ```bash
   cd backend
   poetry install
   ```
3. Set up the frontend:
   ```bash
   cd frontend
   npm install
   ```

### Configuration

1. Create a `.env` file in the `backend` directory with the following variables:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   TAVILY_API_KEY=your_tavily_api_key
   DATABASE_URL=sqlite:///./app.db
   ```

### Running the Application

1. Start the backend:
   ```bash
   cd backend
   poetry run uvicorn app.main:app --reload
   ```
2. Start the frontend:
   ```bash
   cd frontend
   npm start
   ```

## License

This project is licensed under the MIT License.
#   A I - l e d - c o l l a b o r a t o r - r e p o r t - b u i l d e r  
 