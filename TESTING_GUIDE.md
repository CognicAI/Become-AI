# RAG System Testing Guide

This guide shows you how to test the Become AI RAG system step by step.

## 1. Start the Application

First, start the RAG system:

```bash
python start.py
```

You should see:
```
🚀 Starting Become AI RAG System...
✅ Environment checks passed
📊 Configuration loaded
🎯 Starting FastAPI server...
INFO: Uvicorn running on http://0.0.0.0:8000
```

## 2. Test API Endpoints

### Health Check
```bash
# PowerShell
Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing

# Or use curl
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "timestamp": "2025-10-08T20:50:00Z"}
```

### API Documentation
Open your browser and visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 3. Test Website Scraping

### Scrape a Website
```bash
# Using PowerShell
$body = @{
    site_name = "Python Official Docs"
    base_url = "https://docs.python.org/3/"
    description = "Official Python documentation"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8000/scrape -Method POST -Body $body -ContentType "application/json"
```

### Check Scraping Status
```bash
# Replace {job_id} with the actual job ID from the response
Invoke-WebRequest -Uri http://localhost:8000/scrape/status/{job_id} -UseBasicParsing
```

## 4. Test Query System

### Ask a Question
```bash
$query = @{
    question = "How do I create a list in Python?"
    site_base_url = "https://docs.python.org/3/"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8000/query -Method POST -Body $query -ContentType "application/json"
```

## 5. Test with Browser

1. Go to http://localhost:8000/docs
2. Click on `/scrape` endpoint
3. Click "Try it out"
4. Enter test data:
   ```json
   {
     "site_name": "Example Site",
     "base_url": "https://example.com",
     "description": "Test website"
   }
   ```
5. Click "Execute"

## 6. Advanced Testing

### Test Database Directly
```bash
python test_db_connection.py
```

### Test Individual Components
```bash
python test_components.py
```

### Run Unit Tests
```bash
python -m pytest tests/ -v
```

## 7. Performance Testing

### Load Testing with Multiple Requests
```bash
# Test health endpoint performance
for ($i=1; $i -le 10; $i++) {
    Measure-Command { Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing }
}
```

## 8. Common Issues & Solutions

### Server Won't Start
- Check if port 8000 is available: `netstat -an | findstr :8000`
- Verify database connection: `python simple_db_test.py`
- Check logs for error messages

### Scraping Fails
- Verify internet connection
- Check if target website allows scraping (robots.txt)
- Ensure proper URL format (include http/https)

### Query Returns No Results
- Verify the website was scraped successfully
- Check if LM Studio is running on localhost:1234
- Ensure the question relates to scraped content

## 9. Monitoring & Logs

The application logs show:
- Database connections
- Scraping progress  
- Query processing
- Errors and warnings

Watch the console output while testing to see real-time activity.

## 10. Stop the Application

Press `Ctrl+C` in the terminal where the server is running.