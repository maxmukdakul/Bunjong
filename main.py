from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os

app = Flask(__name__, template_folder='room/templates')
app.secret_key = 'your_secret_key_here'

USERS_FILE = 'users.csv'
BOOKINGS_FILE = 'bookings.csv'

# Ensure bookings.csv exists with correct headers
if not os.path.exists(BOOKINGS_FILE):
    with open(BOOKINGS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'name', 'room', 'phone_num', 'people_num', 'slot_type', 'time', 'sales'])

# Load users from CSV
def load_users():
    users = {}
    if not os.path.exists(USERS_FILE):
        return users
    with open(USERS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'username' in row and 'password' in row and 'role' in row:
                users[row['username']] = {
                    'password': row['password'],
                    'role': row['role']
                }
    return users

# Save a new user
def save_user(username, password, role):
    file_exists = os.path.exists(USERS_FILE)
    with open(USERS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists or os.stat(USERS_FILE).st_size == 0:
            writer.writerow(['username', 'password', 'role'])
        writer.writerow([username, password, role])

# Save a new booking
def save_booking(date, name, room, phone_num, people_num, slot_type, time, sales=None):
    file_exists = os.path.exists(BOOKINGS_FILE)
    with open(BOOKINGS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists or os.stat(BOOKINGS_FILE).st_size == 0:
            writer.writerow(['date', 'name', 'room', 'phone_num', 'people_num', 'slot_type', 'time', 'sales'])
        writer.writerow([date, name, room, phone_num, people_num, slot_type, time, sales if sales else ""])

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    users = load_users()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    users = load_users()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username in users:
            return render_template('register.html', error='Username already exists')
        else:
            save_user(username, password, 'user')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/room<int:room_number>', methods=['GET', 'POST'])
def room(room_number):
    if 'username' not in session:
        return redirect(url_for('login'))

    results = []
    selected_date = None
    room_name = f"Room {room_number}"

    if request.method == 'POST':
        selected_date = request.form.get('date', '').strip()
        with open(BOOKINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['date'] == selected_date and row['room'] == room_name:
                    results.append(row)

    return render_template(f'room{room_number}.html', results=results, date=selected_date, room=room_name)

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'username' not in session:
        return redirect(url_for('login'))

    message = ''
    if request.method == 'POST':
        date = request.form.get('date', '').strip()
        name = request.form.get('name', '').strip()
        room = request.form.get('room', '').strip()
        phone_num = request.form.get('phone_num', '').strip()
        people_num = request.form.get('people_num', '').strip()
        slot_type = request.form.get('slot_type', '').strip()
        time = request.form.get('time', '').strip()
        sales = request.form.get('sales', '').strip() if 'sales' in request.form else ""
        save_booking(date, name, room, phone_num, people_num, slot_type, time, sales)
        message = 'Booking saved!'
    return render_template('book.html', message=message)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    search_date = None
    if request.method == 'POST':
        search_date = request.form.get('date', '').strip()
        with open(BOOKINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['date'] == search_date:
                    results.append(row)
    return render_template('search.html', results=results, date=search_date)

if __name__ == '__main__':
    # If users.csv doesn't exist, create it with headers
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password', 'role'])

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)