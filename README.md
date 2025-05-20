# Cloud Search

A tool to search for text through Dropbox cloud storage files.

## Overview

The application consists of two main parts:
1. Python App (with FastAPI and Tesseract)
2. Elasticsearch instance for searching

## Prerequisites

You'll need:
1. Docker Desktop
2. Git

Note: No need to install Elasticsearch or Tesseract - Docker handles that.

## Setup

1. Clone the repository:
```bash
git clone <https://github.com/MohamadAfaneh/cloud_search.git>
cd cloud_search
```

2. Create `.env` file inside the repository and add your Dropbox token:
```
DROPBOX_ACCESS_TOKEN=dropbox_token
```

3. Start the containers:
```bash
docker-compose up --build -d
```

Note : 
before starting the containers Fix this Line Endings (Windows Users Only) :

```bash
dos2unix docker-entrypoint.sh
```

4. Access the application:
- API: https://localhost:8443
- API docs: https://localhost:8443/docs

## Basic Commands

To stop the app:
```bash
docker-compose down
```

To check logs:
```bash
docker-compose logs -f
```

## Supported Files

- PNGs (with OCR)
- PDFs
- Text files
- CSV files

## Testing

Test the search functionality using curl:
```bash
curl -k https://localhost:8443/api/v1/search?q={YOUR_TEXT}
```

## For Development

To rebuild after changes:
```bash
docker-compose down
docker-compose up --build -d
```

## Troubleshooting

If you encounter issues:
1. Check if Docker is running
2. Make sure ports 8443 and 9200 aren't being used
3. Look at the logs: `docker-compose logs -f`
4. Try rebuilding: `docker-compose up --build -d`


## AI Assistant Prompt :
    you find the prompt used to help coding in file ai_assistant_prompts.txt
