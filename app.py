from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO, emit, join_room
from database import get_db_connection, initialize_db, hash_password

app = Flask(__name__)
app.secret_key = "very_secret_key"
socketio = SocketIO(app)
initialize_db()

# ------------------- AUTH ------------------------

@app.route('/')
def index():
    return redirect('/signin')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = hash_password(request.form['password'])
        role = request.form['role']
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (username, email, password, role)
                        VALUES (%s, %s, %s, %s)
                    """, (username, email, password, role))
                    conn.commit()
            return redirect('/signin')
        except Exception as e:
            return render_template('signup.html', error=str(e))
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, role FROM users 
                    WHERE email = %s AND password = %s
                """, (email, password))
                user = cursor.fetchone()

                if user:
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    session['role'] = user[2]
                    return redirect('/home')

        return render_template('signin.html', error="Invalid credentials")
    return render_template('signin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/signin')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect('/signin')
    return render_template('home.html', username=session['username'], role=session['role'])


# ------------------- BOOKINGS ------------------------

@app.route('/book', methods=['GET', 'POST'])
def book_ambulance():
    if 'user_id' not in session:
        return redirect('/signin')

    if request.method == 'POST':
        name = request.form['patient_name']
        phone = request.form['phone_no']
        dest = request.form['destination']
        pickup = "Live GPS"  # Removed manual pickup input

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ambulance_booking (
                        user_id, patient_name, phone_no, pickup_location, destination, status
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (session['user_id'], name, phone, pickup, dest, 'Pending'))
                conn.commit()
        return redirect('/mybookings')

    return render_template('book_ambulance.html', role=session['role'])

@app.route('/mybookings')
def mybookings():
    if 'user_id' not in session:
        return redirect('/signin')

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT b.booking_id, b.patient_name, b.phone_no, b.pickup_location, 
                       b.destination, b.status, b.booking_time, u.username AS driver_name
                FROM ambulance_booking b
                LEFT JOIN users u ON b.driver_id = u.id
                WHERE b.user_id = %s
                ORDER BY b.booking_time DESC
            """, (session['user_id'],))
            bookings = cursor.fetchall()

    return render_template('my_bookings.html', bookings=bookings, role=session['role'])

@app.route('/allbookings')
def all_bookings():
    if session.get('role') != 'admin':
        return redirect('/home')

    status = request.args.get("status")
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = """
                SELECT b.*, u.username 
                FROM ambulance_booking b
                JOIN users u ON b.user_id = u.id
            """
            if status:
                query += " WHERE b.status = %s ORDER BY b.booking_time DESC"
                cursor.execute(query, (status,))
            else:
                query += " ORDER BY b.booking_time DESC"
                cursor.execute(query)
            bookings = cursor.fetchall()

    return render_template('all_bookings.html', bookings=bookings)

@app.route('/driverbookings')
def driver_bookings():
    if session.get('role') != 'driver':
        return redirect('/home')

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT b.booking_id, u.username, b.patient_name, b.phone_no, 
                       b.pickup_location, b.destination, b.status, b.booking_time, b.driver_id
                FROM ambulance_booking b
                JOIN users u ON b.user_id = u.id
                WHERE (b.status = 'Pending' AND b.driver_id IS NULL) 
                      OR b.driver_id = %s
                ORDER BY b.booking_time DESC
            """, (session['user_id'],))
            bookings = cursor.fetchall()

    return render_template("driver_bookings.html", bookings=bookings, driver_id=session['user_id'])

@app.route('/accept_booking/<int:booking_id>')
def accept_booking(booking_id):
    if session.get('role') != 'driver':
        return redirect('/home')

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE ambulance_booking
                SET driver_id = %s, status = 'Accepted'
                WHERE booking_id = %s AND (status = 'Pending' AND driver_id IS NULL)
            """, (session['user_id'], booking_id))
            conn.commit()

    return redirect('/driverbookings')

@app.route('/complete_booking/<int:booking_id>')
def complete_booking(booking_id):
    if session.get('role') != 'driver':
        return redirect('/home')

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE ambulance_booking
                SET status = 'Completed'
                WHERE booking_id = %s AND driver_id = %s
            """, (booking_id, session['user_id']))
            conn.commit()

    return redirect('/driverbookings')

@app.route('/reassign_driver/<int:booking_id>', methods=['GET', 'POST'])
def reassign_driver(booking_id):
    if session.get('role') != 'admin':
        return redirect('/home')

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                new_driver_id = request.form['driver_id']
                cursor.execute("""
                    UPDATE ambulance_booking
                    SET driver_id = %s, status = 'Accepted'
                    WHERE booking_id = %s
                """, (new_driver_id, booking_id))
                conn.commit()
                return redirect('/allbookings')

            cursor.execute("SELECT id, username FROM users WHERE role = 'driver'")
            drivers = cursor.fetchall()
            return render_template("reassign_driver.html", booking_id=booking_id, drivers=drivers)


# ------------------- LOCATION TRACKING ------------------------

@app.route('/update_location', methods=['POST'])
def update_location():
    if session.get('role') != 'driver':
        return "Unauthorized", 401
    data = request.get_json(silent=True)
    if not data or 'latitude' not in data or 'longitude' not in data:
        return "Invalid data", 400

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO driver_location (driver_id, latitude, longitude, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (driver_id) DO UPDATE
                SET latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    updated_at = CURRENT_TIMESTAMP
            """, (session['user_id'], data['latitude'], data['longitude']))
            conn.commit()
    return jsonify(success=True)

@app.route('/get_driver_location/<int:driver_id>')
def get_driver_location(driver_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT latitude, longitude FROM driver_location
                WHERE driver_id = %s
            """, (driver_id,))
            loc = cursor.fetchone()
            if not loc:
                return jsonify(error="Not found"), 404
            return jsonify(lat=loc[0], lng=loc[1])


@app.route('/update_user_location', methods=['POST'])
def update_user_location():
    if session.get('role') != 'user':
        return "Unauthorized", 401
    data = request.get_json(silent=True)
    if not data or 'latitude' not in data or 'longitude' not in data:
        return "Invalid data", 400

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_location (user_id, latitude, longitude, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE
                SET latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    updated_at = CURRENT_TIMESTAMP
            """, (session['user_id'], data['latitude'], data['longitude']))
            print(f"Updated location for driver {session['user_id']} → {data['latitude']}, {data['longitude']}")
            conn.commit()
    return jsonify(success=True)

@app.route('/get_user_location/<int:user_id>')
def get_user_location(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT latitude, longitude FROM user_location
                WHERE user_id = %s
            """, (user_id,))
            loc = cursor.fetchone()
            if not loc:
                return jsonify(error="Not found"), 404
            return jsonify(lat=loc[0], lng=loc[1])
        
        
@app.route('/track_driver/<int:booking_id>')
def track_driver(booking_id):
    if session.get('role') != 'user':
        return redirect('/signin')

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT driver_id FROM ambulance_booking
                WHERE booking_id = %s AND user_id = %s
            """, (booking_id, session['user_id']))
            result = cursor.fetchone()
            if not result or not result[0]:
                return "Driver not assigned", 404

            driver_id = result[0]

    return render_template("track_driver.html", driver_id=driver_id)


@app.route('/get_user_id_from_booking/<int:booking_id>')
def get_user_id_from_booking(booking_id):
    if session.get('role') != 'driver':
        return "Unauthorized", 401

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id FROM ambulance_booking
                WHERE booking_id = %s AND driver_id = %s
            """, (booking_id, session['user_id']))
            result = cursor.fetchone()
            if not result:
                return jsonify(error="Not found"), 404
            return jsonify(user_id=result[0])


# ------------------- RUN APP ------------------------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
