from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'dev_secret'
DB_PATH = 'data.db'

# --- Database setup with fake data ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # schema
    c.executescript("""
    PRAGMA foreign_keys = ON; --yabancı anahtar (foreign key) kısıtlamalarının etkinleştirilmesini sağlar.

    -- Users tablosu
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        user_name TEXT,
        password_hash TEXT,
        phone TEXT,
        email TEXT UNIQUE,
        role_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );

    -- Roles tablosu
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    -- Volunteer Details tablosu
    CREATE TABLE volunteer_details (
        user_id INTEGER PRIMARY KEY,
        expertise TEXT,
        certifications TEXT,
        additional_info TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE -- bir volunteer silindiğinde ona ait kayıtları da siler
    );


    -- Requester Details tablosu
    CREATE TABLE requester_details (
        user_id INTEGER PRIMARY KEY,
        emergency_contact TEXT,
        medical_conditions TEXT,
        additional_info TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Help Requests tablosu
    CREATE TABLE help_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester_id INTEGER,
        location_id INTEGER NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (requester_id) REFERENCES users(id),
        FOREIGN KEY (location_id) REFERENCES locations(id)
    );

    -- Disasters tablosu
    CREATE TABLE disasters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        disaster_type_id INTEGER NOT NULL,
        location_id INTEGER NOT NULL,
        description TEXT,
        started_at DATETIME NOT NULL,
        ended_at DATETIME,
        FOREIGN KEY (disaster_type_id) REFERENCES disaster_types(id),
        FOREIGN KEY (location_id) REFERENCES locations(id)
    );

    -- Disaster Types tablosu
    CREATE TABLE disaster_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    );

    -- Locations tablosu
    CREATE TABLE locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        district TEXT,
        address TEXT,
        postal_code TEXT,
        latitude REAL,
        longitude REAL
    );

    -- Assignments tablosu
    CREATE TABLE assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        volunteer_id INTEGER NOT NULL,
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        accepted BOOLEAN DEFAULT 0,
        completed_at DATETIME,
        FOREIGN KEY (request_id) REFERENCES help_requests(id),
        FOREIGN KEY (volunteer_id) REFERENCES users(id),
        UNIQUE(request_id, volunteer_id)
    );
    """)
    # Add sample data
    try:
        # Roles - auto increment ID kullanarak
        c.execute("INSERT INTO roles (name) VALUES ('coordinator')")
        c.execute("INSERT INTO roles (name) VALUES ('volunteer')")
        c.execute("INSERT INTO roles (name) VALUES ('requester')")
        
        # Role ID'lerini al
        c.execute("SELECT id FROM roles WHERE name='coordinator'")
        coordinator_id = c.fetchone()[0]
        c.execute("SELECT id FROM roles WHERE name='volunteer'")
        volunteer_id = c.fetchone()[0]
        c.execute("SELECT id FROM roles WHERE name='requester'")
        requester_id = c.fetchone()[0]
        
        # Locations
        c.execute("INSERT INTO locations (city, district, address, postal_code, latitude, longitude) VALUES ('Ankara', 'Çankaya', 'Kızılay Meydanı', '06420', 39.92077, 32.85411)")
        c.execute("INSERT INTO locations (city, district, address, postal_code, latitude, longitude) VALUES ('İstanbul', 'Kadıköy', 'Bahariye Caddesi', '34710', 40.99107, 29.02883)")
        c.execute("INSERT INTO locations (city, district, address, postal_code, latitude, longitude) VALUES ('İzmir', 'Konak', 'Alsancak', '35220', 38.41922, 27.12872)")
        c.execute("INSERT INTO locations (city, district, address, postal_code, latitude, longitude) VALUES ('Bursa', 'Osmangazi', 'Heykel', '16010', 40.1826, 29.0668)")
        c.execute("INSERT INTO locations (city, district, address, postal_code, latitude, longitude) VALUES ('Antalya', 'Muratpaşa', 'Konyaaltı Caddesi', '07050', 36.8969, 30.7133)")
        
        # Location ID'lerini al
        c.execute("SELECT id FROM locations WHERE city='Ankara'")
        ankara_id = c.fetchone()[0]
        c.execute("SELECT id FROM locations WHERE city='İstanbul'")
        istanbul_id = c.fetchone()[0]
        
        # Disaster Types
        c.execute("INSERT INTO disaster_types (name, description) VALUES ('Earthquake', 'Deprem')")
        c.execute("INSERT INTO disaster_types (name, description) VALUES ('Flood', 'Su baskını/sel')")
        c.execute("INSERT INTO disaster_types (name, description) VALUES ('Fire', 'Yangın afeti')")
        c.execute("INSERT INTO disaster_types (name, description) VALUES ('Landslide', 'Heyelan')")
        c.execute("INSERT INTO disaster_types (name, description) VALUES ('Tsunami', 'Tsunami')")
        c.execute("INSERT INTO disaster_types (name, description) VALUES ('Avalanche', 'Çığ')")
        
        # Disaster Type ID'lerini al
        c.execute("SELECT id FROM disaster_types WHERE name='Earthquake'")
        earthquake_id = c.fetchone()[0]
        
        # Users with roles
        c.execute("INSERT INTO users (fullname, user_name, password_hash, phone, email, role_id) VALUES ('Ali Koordinatör', 'ali', 'pass', '5551112233', 'ali@example.com', ?)", (coordinator_id,))
        c.execute("INSERT INTO users (fullname, user_name, password_hash, phone, email, role_id) VALUES ('Ayşe Gönüllü', 'ayse', 'pass', '5552223344', 'ayse@example.com', ?)", (volunteer_id,))
        c.execute("INSERT INTO users (fullname, user_name, password_hash, phone, email, role_id) VALUES ('Mehmet Yardım', 'mehmet', 'pass', '5553334455', 'mehmet@example.com', ?)", (requester_id,))
        
        # User ID'lerini al
        c.execute("SELECT id FROM users WHERE email='ayse@example.com'")
        volunteer_user_id = c.fetchone()[0]
        c.execute("SELECT id FROM users WHERE email='mehmet@example.com'")
        requester_user_id = c.fetchone()[0]
        
        # Volunteer details
        c.execute("INSERT INTO volunteer_details (user_id, expertise, certifications, additional_info) VALUES (?, 'İlk Yardım', 'Kızılay Sertifikası', 'Hafta sonları müsait')", (volunteer_user_id,))
        
        # Requester details
        c.execute("INSERT INTO requester_details (user_id, emergency_contact, medical_conditions, additional_info) VALUES (?, 'Fatma Yardım (eşi): 5554443322', 'Yüksek tansiyon', 'İlaçları yanında')", (requester_user_id,))
        
        # Active disasters
        c.execute("INSERT INTO disasters (disaster_type_id, location_id, description, started_at) VALUES (?, ?, '5.8 şiddetinde deprem', '2025-06-04 08:30:00')", (earthquake_id, ankara_id))
        c.execute("INSERT INTO disasters (disaster_type_id, location_id, description, started_at) VALUES (?, ?, 'Sel felaketi', '2025-06-04 10:00:00')", (earthquake_id, istanbul_id))
        
        # Disaster ID'sini al
        c.execute("SELECT id FROM disasters ORDER BY id DESC LIMIT 1")
        disaster_id = c.fetchone()[0]
        
        # Help requests
        c.execute("INSERT INTO help_requests (requester_id, location_id, description, status, created_at) VALUES (?, ?, 'Binada mahsur kaldım, yardım gerekiyor', 'pending', '2025-06-04 09:15:00')", (requester_user_id, ankara_id))
        
        # Help request ID'sini al
        c.execute("SELECT id FROM help_requests ORDER BY id DESC LIMIT 1")
        request_id = c.fetchone()[0]
        
        # Assignments
        c.execute("INSERT INTO assignments (request_id, volunteer_id, assigned_at, accepted) VALUES (?, ?, '2025-06-04 09:30:00', 1)", (request_id, volunteer_user_id))
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    conn.commit()
    conn.close()

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/help', methods=['GET','POST'])
def help_request():
    if request.method == 'POST':
        lat = request.form['lat']
        lng = request.form['lng']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO help_requests(latitude, longitude) VALUES (?,?)", (lat,lng))
        conn.commit()
        conn.close()
        return render_template('help_sended.html')
    return render_template('help.html')


@app.route('/sign-in', methods=['GET','POST'])
def sign_in():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id,role FROM users WHERE email=? AND password_hash=?", (email,pwd))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'], session['role'] = user[0], user[1]
            return redirect(url_for(f"{user[1]}_panel"))
    return render_template('sign_in.html')

@app.route('/sign-up', methods=['GET','POST'])
def sign_up():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        pwd = request.form['password']
        role = request.form['role']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users(fullname,email,password_hash,role) VALUES (?,?,?,?)", (fullname,email,pwd,role))
        conn.commit()
        conn.close()
        return redirect(url_for('sign_in'))
    return render_template('sign_up.html')

@app.route('/volunteer-panel')
def volunteer_panel():
    #if session.get('role')!='volunteer': return redirect(url_for('giris'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id,latitude,longitude,status FROM help_requests WHERE status='pending'")
    requests = c.fetchall()
    conn.close()
    return render_template('volunteer_panel.html', requests=requests)

@app.route('/assign/<int:req_id>')
def assign(req_id):
    if session.get('role')!='volunteer': return redirect(url_for('giris'))
    vid = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO assignments(request_id,volunteer_id) VALUES (?,?)", (req_id, vid))
    c.execute("UPDATE help_requests SET status='assigned' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('volunteer_panel'))

@app.route('/koordinator-panel', methods=['GET','POST'])
def coordinator_panel():
    if session.get('role')!='coordinator': return redirect(url_for('giris'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method=='POST':
        hid = request.form['request_id']
        new_status = request.form['status']
        c.execute("UPDATE help_requests SET status=? WHERE id=?", (new_status, hid))
        conn.commit()
    c.execute("SELECT hr.id,hr.latitude,hr.longitude,hr.status,u.fullname FROM help_requests hr LEFT JOIN assignments a ON hr.id=a.request_id LEFT JOIN users u ON a.volunteer_id=u.id")
    data = c.fetchall()
    conn.close()
    return render_template('coordinator_panel.html', data=data)

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True)

# --- Templates (templates/ folder) ---
# index.html, help.html, help_sended.html, 
# sign_in.html, sign_up.html, volunteer_panel.html, coordinator_panel.html

