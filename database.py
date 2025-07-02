
import os
import psycopg2
import hashlib
import urllib.parse as urlparse

# def get_db_connection():
#     result = urlparse.urlparse(os.environ['DATABASE_URL'])
#     username = result.username
#     password = result.password
#     database = result.path[1:]
#     hostname = result.hostname
#     port = result.port

#     return psycopg2.connect(
#         database=database,
#         user=username,
#         password=password,
#         host=hostname,
#         port=port
#     )

# # def get_db_connection():
# #     return psycopg2.connect(
# #         database="ambulance_db",
# #         user="postgres",
# #         password="@hybesty123",  # 🔐 Change for production
# #         host="127.0.0.1",
# #         port=5432
# #     )

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
# def initialize_db():
#     # Step 1: Create ambulance_db if it doesn't exist
#     admin_conn = psycopg2.connect(
#         database="postgres",
#         user="postgres",
#         password="@hybesty123",
#         host="127.0.0.1",
#         port=5432
#     )
#     admin_conn.autocommit = True

#     with admin_conn.cursor() as cursor:
#         cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'ambulance_db'")
#         if cursor.fetchone() is None:
#             cursor.execute("CREATE DATABASE ambulance_db")

#     admin_conn.close()

#     # Step 2: Create tables in ambulance_db
#     with get_db_connection() as conn:
#         with conn.cursor() as cursor:
#             # Users table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS users (
#                     id SERIAL PRIMARY KEY,
#                     username VARCHAR(100),
#                     email VARCHAR(100) UNIQUE,
#                     password VARCHAR(255),
#                     role VARCHAR(20) DEFAULT 'user'
#                 );
#             """)

#             # Ambulance bookings
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS ambulance_booking (
#                     booking_id SERIAL PRIMARY KEY,
#                     user_id INTEGER REFERENCES users(id),
#                     driver_id INTEGER REFERENCES users(id),
#                     patient_name VARCHAR(100),
#                     phone_no VARCHAR(20),
#                     pickup_location TEXT,
#                     destination TEXT,
#                     booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     status VARCHAR(50) DEFAULT 'Pending'
#                 );
#             """)

#             # Driver live location
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS driver_location (
#                     driver_id INTEGER PRIMARY KEY REFERENCES users(id),
#                     latitude DOUBLE PRECISION,
#                     longitude DOUBLE PRECISION,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 );
#             """)

#             # User live location
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS user_location (
#                     user_id INTEGER PRIMARY KEY REFERENCES users(id),
#                     latitude DOUBLE PRECISION,
#                     longitude DOUBLE PRECISION,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 );
#             """)

#             # Default admin user
#             default_email = 'raj@gmail.com'
#             default_password = hash_password('raj123')
#             cursor.execute("""
#                 INSERT INTO users (username, email, password, role)
#                 SELECT %s, %s, %s, %s
#                 WHERE NOT EXISTS (
#                     SELECT 1 FROM users WHERE email = %s
#                 );
#             """, ('raj', default_email, default_password, 'admin', default_email))

#         conn.commit()





# for render.com

def initialize_db():
    db_url = os.environ['DATABASE_URL']
    result = urlparse.urlparse(db_url)

    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )

    with conn.cursor() as cursor:
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                password VARCHAR(255),
                role VARCHAR(20) DEFAULT 'user'
            );
        """)

        # Ambulance bookings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ambulance_booking (
                booking_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                driver_id INTEGER REFERENCES users(id),
                patient_name VARCHAR(100),
                phone_no VARCHAR(20),
                pickup_location TEXT,
                destination TEXT,
                booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'Pending'
            );
        """)

        # Driver live location
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS driver_location (
                driver_id INTEGER PRIMARY KEY REFERENCES users(id),
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # User live location
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_location (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Default admin user
        default_email = 'raj@gmail.com'
        default_password = hash_password('raj123')
        cursor.execute("""
            INSERT INTO users (username, email, password, role)
            SELECT %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM users WHERE email = %s
            );
        """, ('raj', default_email, default_password, 'admin', default_email))

    conn.commit()
    conn.close()
