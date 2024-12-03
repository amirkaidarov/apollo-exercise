run test:

FLASK_ENV=testing
FLASK_ENV=production
env/bin/python -m pytest test/tests.py    


setup db:
psql -U postgres -f app/database-create.sql


setup:
define .env