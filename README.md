# Birthday Builder Backend

This is the backend for the Birthday Builder platform, built with FastAPI and Supabase.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone [your-repo-url]
    cd birthday-builder-backend
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Copy the `.env.example` file to `.env` and fill in your Supabase and JWT details.
    ```bash
    cp .env.example .env
    ```

4.  **Run Migrations:**
    The Supabase schema is defined in `migrations/supabase_schema.sql`. You can apply this schema directly to your Supabase project.

5.  **Run the application:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

    The API documentation will be available at `http://localhost:8000/docs`.

## Docker
To build and run the application using Docker:

```bash
docker-compose up --build
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   │
│   ├── models/
│   │   ├── ...
│   │
│   ├── schemas/
│   │   ├── ...
│   │
│   ├── api/
│   │   ├── v1/
│   │   │   ├── ...
│   │
│   ├── services/
│   │   ├── ...
│   │
│   ├── middleware/
│   │   ├── ...
│   │
│   └── utils/
│       ├── ...
│
├── migrations/
│   └── supabase_schema.sql
│
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```
