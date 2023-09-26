# Backend - Analyzer

## How to use this Code Locally

### 1. Install and activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
``` 

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Uvicorn server
```bash
uvicorn main:app --reload
```

### 4. Open the API documentation
```bash
http://localhost:8000/docs
```

## Deploy to AWS Elastic Beanstalk

### 1. Create a new Elastic Beanstalk application
```bash
eb init -p python-3.9 analyzer
```

### 2. Create a new Elastic Beanstalk environment
```bash
eb create analyzer-env
```

### 3. Deploy the application to Elastic Beanstalk
```bash
eb deploy analyzer-env --staged --profile analyzer  --region us-east-1 
```

### 4. Open the API documentation
```bash
eb open analyzer-env --profile analyzer  --region us-east-1 
```

## Deploy from Console

### 1. Follow [these steps to deploy the EB from the AWS Console](https://www.youtube.com/watch?v=guFsZB8r89M)

### 2. Zip the project

### 3. Procfile, Main.py and requirements.txt should be in the root of the zip file
```bash
zip -r analyzer.zip . main.py Procfile requirements.txt
```


