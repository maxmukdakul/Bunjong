from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os

app = Flask(__name__, template_folder='room/templates')
app.secret_key = 'your_secret_key_here'

USERS_FILE = 'users.csv'

# Load users from CSV
def load_users():
    users = {}
    with open('users.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
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
            writer.writerow(['username', 'password', 'role'])  # write header if file is empty
        writer.writerow([username, password, role])


@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    users = load_users()  # dict with username: {'password': ..., 'role': ...}
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']  # ✅ Save role into session
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    users = load_users()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            return render_template('register.html', error='Username already exists')
        else:
            save_user(username, password, 'user')  # Always saved as 'user'
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
        selected_date = request.form['date']
        with open('bookings.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['date'] == selected_date and row['room'] == room_name:
                    results.append(row)

    return render_template(f'room{room_number}.html', results=results, date=selected_date, room=room_name)


@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        search_date = request.form['date']
        with open('bookings.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['date'] == search_date:
                    results.append(row)
    return render_template('search.html', results=results)

@app.route('/available', methods=['GET', 'POST'])
def available():
    all_rooms = [f"Room {i}" for i in range(1, 11)]
    available_rooms = all_rooms
    selected_date = None
    slot_type = None
    start_time = None
    end_time = None

    if request.method == 'POST':
        selected_date = request.form['date']
        slot_type = request.form['slot_type']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        selected_time = f"{slot_type}|{start_time}-{end_time}"
        booked_rooms = set()

        with open('bookings.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['date'] == selected_date and row['time'] == selected_time:
                    booked_rooms.add(row['room'])

        available_rooms = [room for room in all_rooms if room not in booked_rooms]

    return render_template(
        'available.html',
        rooms=available_rooms,
        date=selected_date,
        slot_type=slot_type,
        start_time=start_time,
        end_time=end_time
    )

@app.route('/book_room', methods=['GET', 'POST'])
def book_room():
    if 'username' not in session:
        return redirect(url_for('login'))

    room = request.args.get('room')
    date = request.args.get('date')
    slot_type = request.args.get('slot_type')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    if not room or not date or not slot_type or not start_time or not end_time:
        return "Missing booking information. Please start from the available rooms page.", 400

    selected_time = f"{slot_type}|{start_time}-{end_time}"

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        people = request.form['people']
        sales = request.form['sales']

        booking_data = [date, name, room, phone, people, selected_time, sales]
        file_exists = os.path.isfile('bookings.csv')
        write_header = not file_exists or os.stat('bookings.csv').st_size == 0

        with open('bookings.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(['date', 'name', 'room', 'phone_num', 'people_num', 'time', 'sales'])
            writer.writerow(booking_data)

        return redirect(url_for('index'))

    return render_template(
        'book_form.html',
        room=room,
        date=date,
        slot_type=slot_type,
        start_time=start_time,
        end_time=end_time
    )


if __name__ == '__main__':
    # If users.csv doesn't exist, create it with headers
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password', 'role'])

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
