from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os

app = Flask(__name__, template_folder='room/templates')
app.secret_key = 'your_secret_key_here'

USERS_FILE = 'users.csv'
BOOKINGS_FILE = 'bookings.csv'

SLOT_TIMES = {
    'half_morning': ('08.00', '12.00'),
    'half_afternoon': ('13.00', '17.00'),
    'fullday': ('08.00', '17.00'),
    'night': ('18.00', '22.00')
}

# Load users from CSV
def load_users():
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
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
            writer.writerow(['username', 'password', 'role'])
        writer.writerow([username, password, role])

# Save a booking
def save_booking(date, name, room, phone_num, people_num, slot_type, time, sales):
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
        username = request.form['username']
        password = request.form['password']

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
        username = request.form['username']
        password = request.form['password']

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
        selected_date = request.form['date']
        if os.path.exists(BOOKINGS_FILE):
            with open(BOOKINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    if row['date'] == selected_date and row['room'] == room_name:
                        row['booking_id'] = idx  # Add booking_id here
                        results.append(row)

    return render_template(f'room{room_number}.html', results=results, date=selected_date, room=room_name)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        search_date = request.form['date']
        if os.path.exists(BOOKINGS_FILE):
            with open(BOOKINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['date'] == search_date:
                        results.append(row)
    return render_template('search.html', results=results)

@app.route('/available', methods=['GET', 'POST'])
def available():
    all_rooms = [f"Room {i}" for i in range(1, 11)]
    available_rooms = all_rooms.copy()
    selected_date = slot_type_full = slot_type = ""
    time_range = ""

    if request.method == 'POST':
        selected_date = request.form['date'].strip()
        slot_type_full = request.form['slot_type'].strip()

        if '|' in slot_type_full:
            slot_type, time_range = slot_type_full.split('|')

            booked_rooms = set()
            if os.path.exists(BOOKINGS_FILE):
                with open(BOOKINGS_FILE, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['date'].strip() == selected_date and row['slot_type'].strip() == slot_type:
                            booked_rooms.add(row['room'].strip())

            available_rooms = [room for room in all_rooms if room not in booked_rooms]

    return render_template(
        'available.html',
        rooms=available_rooms,
        date=selected_date,
        slot_type=slot_type_full,
        time_range=time_range
    )

@app.route('/book_room', methods=['GET', 'POST'])
def book_room():
    if 'username' not in session:
        return redirect(url_for('login'))

    room = request.args.get('room')
    date = request.args.get('date')
    slot_type = request.args.get('slot_type')

    if not room or not date or not slot_type:
        return "Missing booking information. Please start from the available rooms page.", 400

    time_range = slot_type.split('|')[1]
    slot_key = slot_type.split('|')[0]
    new_start, new_end = SLOT_TIMES[slot_key]
    error = None

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        people = request.form['people']
        sales = request.form['sales']

        if os.path.exists(BOOKINGS_FILE):
            with open(BOOKINGS_FILE, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['date'] == date and row['room'] == room:
                        existing_start, existing_end = SLOT_TIMES.get(row['slot_type'], ("00.00", "00.00"))
                        if times_overlap(new_start, new_end, existing_start, existing_end):
                            error = "This room is already booked at an overlapping time."
                            return render_template(
                                'book_form.html', room=room, date=date, slot_type=slot_type,
                                time_range=time_range, error=error
                            )

        save_booking(date, name, room, phone, people, slot_key, time_range, sales)
        return redirect(url_for('index'))

    return render_template(
        'book_form.html', room=room, date=date,
        slot_type=slot_type, time_range=time_range, error=error
    )


@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    if 'username' not in session or session.get('role') != 'admin':
        return "Access denied", 403

    if not os.path.exists(BOOKINGS_FILE):
        return "Booking file not found", 404

    with open(BOOKINGS_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        bookings = list(reader)

    if booking_id < 0 or booking_id >= len(bookings):
        return "Booking not found", 404

    booking = bookings[booking_id]
    error = None

    if request.method == 'POST':
        new_date = request.form['date']
        new_name = request.form['name']
        new_phone = request.form['phone']
        new_people = request.form['people']
        new_slot_type = request.form['slot_type']
        new_time = request.form['time']
        new_sales = request.form['sales']
        new_room = request.form['room']
        new_start, new_end = SLOT_TIMES[new_slot_type]

        for i, row in enumerate(bookings):
            if i == booking_id:
                continue
            if row['date'] == new_date and row['room'] == new_room:
                existing_start, existing_end = SLOT_TIMES.get(row['slot_type'], ("00.00", "00.00"))
                if times_overlap(new_start, new_end, existing_start, existing_end):
                    error = "The selected room is already booked at an overlapping time."
                    return render_template('edit_booking.html', booking=booking, booking_id=booking_id, error=error)

        booking['date'] = new_date
        booking['name'] = new_name
        booking['phone_num'] = new_phone
        booking['people_num'] = new_people
        booking['slot_type'] = new_slot_type
        booking['time'] = new_time
        booking['sales'] = new_sales
        booking['room'] = new_room

        with open(BOOKINGS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=booking.keys())
            writer.writeheader()
            writer.writerows(bookings)

        return redirect(url_for('index'))

    return render_template('edit_booking.html', booking=booking, booking_id=booking_id, error=error)


@app.route('/booked_rooms', methods=['GET', 'POST'])
def booked_rooms():
    bookings = []
    selected_date = None

    if request.method == 'POST':
        selected_date = request.form['date']
        if os.path.exists(BOOKINGS_FILE):
            with open(BOOKINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    if row['date'].strip() == selected_date.strip():
                        row['booking_id'] = idx
                        bookings.append(row)

        # Sort bookings by room number (Room 1 to Room 10)
        bookings.sort(key=lambda x: int(x['room'].split()[-1]))

    return render_template('booked_rooms.html', date=selected_date, bookings=bookings)

@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    if 'username' not in session or session.get('role') != 'admin':
        return "Access denied", 403

    if not os.path.exists(BOOKINGS_FILE):
        return "Booking file not found", 404

    with open(BOOKINGS_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        bookings = list(reader)

    if booking_id < 0 or booking_id >= len(bookings):
        return "Booking not found", 404

    # Remove the booking at booking_id
    bookings.pop(booking_id)

    # Rewrite the CSV without the deleted booking
    with open(BOOKINGS_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'name', 'room', 'phone_num', 'people_num', 'slot_type', 'time', 'sales'])
        writer.writeheader()
        writer.writerows(bookings)

    return redirect(url_for('booked_rooms'))

def times_overlap(start1, end1, start2, end2):
    return max(start1, start2) < min(end1, end2)


if __name__ == '__main__':
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password', 'role'])

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
