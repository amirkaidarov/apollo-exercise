# Project README

## Overview

This is an implementation of Apollo exercise with based on Flask application and PostgreSQL database. It is deployed at  http://3.83.231.140:5000 with AWS.

## Requirements

- Python 3.x
- PostgreSQL

## Setup Instructions

### 1. Clone the Repository

Clone the repository to your local machine:

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Environment Configuration
Create two .env files for production (.env) and testing (.env.test) environments with following variables:

```plaintext
DB_NAME=<db_name>
DB_USER=<db_user>
DB_PASSWORD=<db_password>
DB_HOST=<db_host>
DB_PORT=<db_port>
```

Place these files in the root directory of the project

### 3. Install Dependencies

To set up the virtual environment and install the required dependencies from requirements.txt, run the following command:

```bash
make setup
```

### 4. Database Setup
The project requires a PostgreSQL database (for testing and production).

To Set Up the Production Database:
```bash
make setup-prod-db
```

To Set Up the Testing Database:

```bash
make setup-test-db
```

### 5. Running the Application
To run the application, execute the following command:

```bash
make run
```
This will start the Flask application on http://127.0.0.1:5001.

### 6. Running Tests
To run tests, first set up the testing database, and then run the tests:

```bash
make setup-test-db  
make test           
```