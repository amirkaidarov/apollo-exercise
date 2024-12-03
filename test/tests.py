import sys
import os
import pytest
import uuid
from app.app import app, get_db_connection
from psycopg2.extras import RealDictCursor
from psycopg2.errors import UniqueViolation
from decimal import Decimal

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def init_db():
    # Reset the database
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Drop and create the VEHICLES table
    cur.execute("DROP TABLE IF EXISTS VEHICLES;")
    cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    cur.execute("CREATE EXTENSION IF NOT EXISTS citext;")
    cur.execute("""
        CREATE TABLE VEHICLES (
            VID varchar NOT NULL DEFAULT uuid_generate_v4(), 
            VIN citext NOT NULL,
            MANUFACTURER_NAME varchar NOT NULL,
            DESCRIPTION varchar NOT NULL,
            HORSE_POWER int NOT NULL,
            MODEL_NAME varchar NOT NULL,
            MODEL_YEAR int NOT NULL,
            PURCHASE_PRICE decimal(20, 2) NOT NULL,
            FUEL_TYPE varchar NOT NULL,
            CONSTRAINT VEHICLE_pk PRIMARY KEY (VID),
            CONSTRAINT VIN_uniq UNIQUE (VIN)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def normalize_vehicle_data(vehicle):
    return {
        "vid": str(vehicle["vid"]),
        "vin": vehicle["vin"],
        "manufacturer_name": vehicle["manufacturer_name"],
        "description": vehicle["description"],
        "horse_power": vehicle["horse_power"],
        "model_name": vehicle["model_name"],
        "model_year": vehicle["model_year"],
        "purchase_price": float(vehicle["purchase_price"]) if isinstance(vehicle["purchase_price"], Decimal) else float(vehicle["purchase_price"]),
        "fuel_type": vehicle["fuel_type"]
    }

def test_get_no_vehicles(client, init_db):
    response = client.get('/vehicle')
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) == 0, "Number of vehilces should be zero"

def test_get_vehicles(client, init_db):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO VEHICLES (VIN, MANUFACTURER_NAME, DESCRIPTION, HORSE_POWER, MODEL_NAME, MODEL_YEAR, PURCHASE_PRICE, FUEL_TYPE)
        VALUES
            ('4Y1SL65848Z411439', 'Toyota', 'red', 120, 'Camry', 2020, 20000.00, 'Petrol'),
            ('4Y1SL65848Z411438', 'Tesla', 'nice', 300, 'Model 3', 2022, 40000.00, 'Petrol'),
            ('4Y1SL65848Z411437', 'Ford', 'is it a mustang?', 250, 'Mustang', 2021, 35000.00, 'Petrol');
    """)
    conn.commit()
    cur.close()
    conn.close()

    response = client.get('/vehicle')

    assert response.status_code == 200
    assert isinstance(response.json, list), "Response should be a list of vehicles"

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM VEHICLES;")
    db_result = cur.fetchall()
    cur.close()
    conn.close()

    assert len(response.json) == len(db_result), "Incorrect number of vehicles returned"

    api_data = [normalize_vehicle_data(vehicle) for vehicle in response.json]
    db_data = [normalize_vehicle_data(dict(row)) for row in db_result]

    assert api_data == db_data, "Incorrect data returned"


def test_post_vehicle(client, init_db):
    payload = {
        "vin": "4Y1SL65848Z411439",
        "manufacturer_name": "Toyota",
        "description": "Very good",
        "horse_power": 200,
        "model_name": "Camry",
        "model_year": 2020,
        "purchase_price": 25000.00,
        "fuel_type": "Petrol"
    }
    
    response = client.post('/vehicle', json=payload)
    assert response.status_code == 201
    assert "vin" in response.json

    try:
        uuid.UUID(response.json['vid'])
    except ValueError:
        pytest.fail("VID is not a valid UUID")
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM VEHICLES WHERE VIN = %s;", (payload["vin"],))
    db_result = cur.fetchone()
    cur.close()
    conn.close()

    assert db_result is not None, "Vehicle was not added to the database"

    normalized_db_result = normalize_vehicle_data(db_result)
    expected_payload = payload.copy()
    expected_payload["vid"] = response.json["vid"]

    assert normalized_db_result == expected_payload

def test_get_vehicle(client, init_db):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO VEHICLES (VIN, MANUFACTURER_NAME, DESCRIPTION, HORSE_POWER, MODEL_NAME, MODEL_YEAR, PURCHASE_PRICE, FUEL_TYPE)
        VALUES ('4Y1SL65848Z411439', 'Ford', 'very cool', 250, 'Mustang', 2022, 55000.00, 'Petrol')
        RETURNING VIN;
    """)
    vin = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    response = client.get(f'/vehicle/{vin}')
    assert response.status_code == 200
    assert response.json['vin'] == vin

def test_get_vehicle_not_exist(client, init_db):
    response = client.get('/vehicle/4Y1SL65848Z411439')
    assert response.status_code == 404

def test_put_vehicle(client, init_db):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO VEHICLES (VIN, MANUFACTURER_NAME, DESCRIPTION, HORSE_POWER, MODEL_NAME, MODEL_YEAR, PURCHASE_PRICE, FUEL_TYPE)
        VALUES ('4Y1SL65848Z411439', 'Chevrolet', 'insane', 150, 'Version One', 2020, 22000.00, 'Gasoline')
        RETURNING VIN;
    """)
    vin = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    updated_payload = {
        "vin": "4Y1SL65848Z411439",
        "manufacturer_name": "Not a Chevrolet",
        "description": "new",
        "horse_power": 160,
        "model_name": "Version Two",
        "model_year": 2021,
        "purchase_price": 23000.00,
        "fuel_type": "GasolineGasoline"
    }

    response = client.put(f'/vehicle/{vin}', json=updated_payload)
    assert response.status_code == 200

    # Check that updated vehicle is returned
    assert response.json['vin'] == updated_payload['vin']
    assert response.json['manufacturer_name'] == updated_payload['manufacturer_name']
    assert response.json['description'] == updated_payload['description']
    assert response.json['horse_power'] == updated_payload['horse_power']
    assert response.json['model_name'] == updated_payload['model_name']
    assert response.json['model_year'] == updated_payload['model_year']
    assert float(response.json['purchase_price']) == float(updated_payload['purchase_price'])
    assert response.json['fuel_type'] == updated_payload['fuel_type']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM VEHICLES WHERE VIN = %s;", (vin,))
    db_result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    # Check that the database is updated
    assert db_result is not None, "Vehicle was not found in the database"
    assert db_result['vin'] == updated_payload['vin']
    assert db_result['manufacturer_name'] == updated_payload['manufacturer_name']
    assert db_result['description'] == updated_payload['description']
    assert db_result['horse_power'] == updated_payload['horse_power']
    assert db_result['model_name'] == updated_payload['model_name']
    assert db_result['model_year'] == updated_payload['model_year']
    assert float(db_result['purchase_price']) == float(updated_payload['purchase_price'])
    assert db_result['fuel_type'] == updated_payload['fuel_type']


def test_put_vehicle_not_exist(client, init_db):
    updated_payload = {
        "vin": "4Y1SL65848Z411439",
        "manufacturer_name": "Not a Chevrolet",
        "description": "new",
        "horse_power": 160,
        "model_name": "Version Two",
        "model_year": 2021,
        "purchase_price": 23000.00,
        "fuel_type": "GasolineGasoline"
    }
    response = client.put('/vehicle/4Y1SL65848Z411439', json=updated_payload)
    assert response.status_code == 404

def test_delete_vehicle(client, init_db):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO VEHICLES (VIN, MANUFACTURER_NAME, DESCRIPTION, HORSE_POWER, MODEL_NAME, MODEL_YEAR, PURCHASE_PRICE, FUEL_TYPE)
        VALUES ('4Y1SL65848Z411439', 'Tesla', 'electric', 350, 'Model S', 2023, 80000.00, 'Electric')
        RETURNING VIN;
    """)
    vin = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    response = client.delete(f'/vehicle/{vin}')
    assert response.status_code == 204

    response = client.get(f'/vehicle/{vin}')
    assert response.status_code == 404



def test_post_invalid_json_payload_vehicle(client, init_db):
    invalid_payload = "notajson"
    response = client.post('/vehicle', data=invalid_payload, content_type='application/json')
    assert response.status_code == 400
    assert response.json['error'] == "Invalid JSON payload"

def test_put_invalid_json_payload_vehicle(client, init_db):
    invalid_payload = "notajson"
    response = client.put('/vehicle/4Y1SL65848Z411439', data=invalid_payload, content_type='application/json')
    assert response.status_code == 400
    assert response.json['error'] == "Invalid JSON payload"

def test_post_missing_required_fields_vehicle(client, init_db):
    incomplete_payload = {"vin": "4Y1SL65848Z411439"} 
    response = client.post('/vehicle', json=incomplete_payload)
    assert response.status_code == 400
    assert response.json['error'] == "Missing required fields"

def test_put_missing_required_fields_vehicle(client, init_db):
    incomplete_payload = {"vin": "4Y1SL65848Z411439"} 
    response = client.put('/vehicle/4Y1SL65848Z411439', json=incomplete_payload)
    assert response.status_code == 400
    assert response.json['error'] == "Missing required fields"

def test_post_invalid_data_types_vehicle(client, init_db):
    invalid_data_payload = {
        "vin": 12345,  # has to be a string
        "manufacturer_name": "Toyota",
        "description": "nicd",
        "horse_power": 1,
        "model_name": "Corola",
        "model_year": 2020,
        "purchase_price": 20000,
        "fuel_type": "Petrol"
    }
    response = client.post('/vehicle', json=invalid_data_payload)
    assert response.status_code == 422
    assert response.json['error'] == "Invalid data types"

def test_post_invalid_null_vehicle(client, init_db):
    invalid_data_payload = {
        "vin": "4Y1SL65848Z411439",
        "manufacturer_name": None, # should not be null 
        "description": "nicd",
        "horse_power": 1,
        "model_name": "Corola",
        "model_year": 2020,
        "purchase_price": 20000,
        "fuel_type": "Petrol"
    }
    response = client.post('/vehicle', json=invalid_data_payload)
    assert response.status_code == 422
    assert response.json['error'] == "Invalid data types"

def test_vin_uniqueness(client, init_db):
    payload_1 = {
        "vin": "VIN12345_",
        "manufacturer_name": "Toyota",
        "description": "A reliable car",
        "horse_power": 150,
        "model_name": "Corolla",
        "model_year": 2020,
        "purchase_price": 20000.00,
        "fuel_type": "Gasoline"
    }

    payload_2 = {
        "vin": "vIn12345_",  # Case-insensitive duplicate VIN
        "manufacturer_name": "Honda",
        "description": "A compact car",
        "horse_power": 140,
        "model_name": "Civic",
        "model_year": 2021,
        "purchase_price": 22000.00,
        "fuel_type": "Gasoline"
    }

    response_1 = client.post('/vehicle', json=payload_1)
    assert response_1.status_code == 201, "First vehicle creation failed."

    response_2 = client.post('/vehicle', json=payload_2)
    assert response_2.status_code == 422, "Second vehicle creation with duplicate VIN should fail."

def test_vin_update(client, init_db):
    payload_1 = {
        "vin": "VIN12345_",
        "manufacturer_name": "Toyota",
        "description": "nicd",
        "horse_power": 150,
        "model_name": "Corola",
        "model_year": 2020,
        "purchase_price": 20000.00,
        "fuel_type": "Petrol"
    }

    payload_2 = {
        "vin": "VIN123456",
        "manufacturer_name": "Toyota",
        "description": "nicd",
        "horse_power": 150,
        "model_name": "Corola",
        "model_year": 2020,
        "purchase_price": 20000.00,
        "fuel_type": "Petrol"
    }

    payload_3 = {
        "vin": "VIN123456",  # attempt to update vin that is already in use 
        "manufacturer_name": "Toyotaa",
        "description": "nicd",
        "horse_power": 150,
        "model_name": "Corola",
        "model_year": 2020,
        "purchase_price": 20000.00,
        "fuel_type": "Petrol"
    }

    response_1 = client.post('/vehicle', json=payload_1)
    assert response_1.status_code == 201, "First vehicle creation failed."
    
    response_2 = client.post('/vehicle', json=payload_2)
    assert response_2.status_code == 201, "Second vehicle creation failed."

    response_2 = client.put('/vehicle/VIN12345_', json=payload_3)
    assert response_2.status_code == 422, "Updating vehicle with existing vin should fail."