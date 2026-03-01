# Auto-Job-Apply-Agent

## Docker

Create `.env` file or `docker.env`

**template**:
```DB_URL=postgresql://postgres:postgres@localhost:5432/jobs
DB_URL_DOCKER=postgresql+psycopg2://jobs:jobs@app-db:5432/jobs
API_URL=http://127.0.0.1:8000
JOB_API_BASE_URL=http://api:8000
CRAWL_TITLE=Data Scientist
CRAWL_LOCATION=Paris
CRAWL_COUNT=30
```

### Start

```bash
docker compose up --build -d
```

**Ports**
- API: `http://127.0.0.1:8000`
- Airflow UI: `http://127.0.0.1:8080`

**Airflow Login**：
- username: `admin`
- password: `admin`

**psql DB**
```
docker exec -it job_app_db psql -U jobs -d jobs
```

### Stop

```bash
docker compose down
```

**Clean image**：

```bash
docker compose down -v
```
