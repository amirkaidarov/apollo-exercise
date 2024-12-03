import os
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv('.env.test' if os.getenv('TESTING') == 'True' else '.env')
app = Flask(__name__)

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except psycopg2.Error as e:
        raise RuntimeError(f"Failed to connect to database: {e}")
    
def validate_vehicle_data(data):
    required_fields = {
        "vin": str,
        "manufacturer_name": str,
        "description": str,
        "horse_power": int,
        "model_name": str,
        "model_year": int,
        "purchase_price": (int, float),
        "fuel_type": str
    }
    
    # Check if all required fields are present 
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return False, {'error': 'Missing required fields'}, 400

    # Check if all requried fields are of correct data type 
    for field, expected_type in required_fields.items():
        if not isinstance(data.get(field), expected_type):
            return False,{'error': 'Invalid data types'}, 422 

    # No errors
    return True, None, None

@app.route('/vehicle')
def get_vehicles():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM Vehicles")
        vehicles = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(vehicles), 200
    except psycopg2.Error as e:
        return {"error": f"Database error: {e}"}, 500

@app.route('/vehicle', methods=['POST'])
def create_vehicle():
    data = request.get_json(silent=True)
    if not data: return jsonify({'error': 'Invalid JSON payload'}), 400

    is_valid, error_response, status_code = validate_vehicle_data(data)
    if not is_valid: return jsonify(error_response), status_code

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            INSERT INTO Vehicles (vin, manufacturer_name, description, horse_power, model_name, model_year, purchase_price, fuel_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING vid, vin, manufacturer_name, description, horse_power, model_name, model_year, purchase_price, fuel_type
            """,
            (
                data['vin'],
                data['manufacturer_name'], 
                data['description'],
                data['horse_power'], 
                data['model_name'], 
                data['model_year'],
                data['purchase_price'], 
                data['fuel_type']
            )
        )
        new_vehicle = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(new_vehicle), 201
    except psycopg2.errors.UniqueViolation:
        return {"error": "VIN must be unique"}, 422
    except psycopg2.Error as e:
        return {"error": "Database Error"}, 500
    except:
        return {"error": f"Unexpected error occured"}, 500

@app.route('/vehicle/<string:vin>')
def get_vehicle(vin):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM Vehicles WHERE vin = %s", (vin,))
        vehicle = cur.fetchone()
        cur.close()
        conn.close()
        if vehicle: return jsonify(vehicle), 200
        return {"error": "Vehicle not found"}, 404
    except psycopg2.Error as e:
        return {"error": f"Database error: {e}"}, 500
    except:
        return {"error": f"Unexpected error occured"}, 500

@app.route('/vehicle/<string:vin>', methods=['PUT'])
def update_vehicle(vin):
    data = request.get_json(silent=True)
    if not data: return jsonify({'error': 'Invalid JSON payload'}), 400

    is_valid, error_response, status_code = validate_vehicle_data(data)
    if not is_valid: return jsonify(error_response), status_code

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            UPDATE Vehicles
            SET vin = %s, 
                manufacturer_name = %s, 
                description = %s, 
                horse_power = %s,
                model_name = %s, 
                model_year = %s, 
                purchase_price = %s, 
                fuel_type = %s
            WHERE vin = %s
            RETURNING vid, vin, manufacturer_name, description, horse_power, model_name, model_year, purchase_price, fuel_type
            """,
            (
                data['vin'],
                data['manufacturer_name'], 
                data['description'], 
                data['horse_power'],
                data['model_name'], 
                data['model_year'], 
                data['purchase_price'],
                data['fuel_type'], 
                vin
            )
        )
        updated_vehicle = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_vehicle: return jsonify(updated_vehicle), 200
        return {"error": "Vehicle not found"}, 404
    except psycopg2.errors.UniqueViolation:
        return {"error": "VIN must be unique"}, 422
    except psycopg2.Error as e:
        return {"error": f"Database error: {e}"}, 500
    except:
        return {"error": f"Unexpected error occured"}, 500

@app.route('/vehicle/<string:vin>', methods=['DELETE'])
def delete_vehicle(vin):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM Vehicles WHERE vin = %s", (vin,))
        conn.commit()
        cur.close()
        conn.close()
        return '', 204
    except psycopg2.Error as e:
        return {"error": f"Database error: {e}"}, 500
    except:
        return {"error": f"Unexpected error occured"}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
