# app.py - Flask Application with Supabase
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import re

# Load environment variables
load_dotenv()

# Debug: Check if .env is loaded
print("DEBUG: Checking environment variables...")
print(f"SUPABASE_URL exists: {os.getenv('SUPABASE_URL') is not None}")
print(f"SUPABASE_KEY exists: {os.getenv('SUPABASE_KEY') is not None}")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

# Validate environment variables
if not supabase_url or not supabase_key:
    print("\n❌ ERROR: Missing Supabase credentials!")
    print("Please check your .env file contains:")
    print("  - SUPABASE_URL=your-project-url")
    print("  - SUPABASE_KEY=your-anon-key")
    print(f"\nCurrent values:")
    print(f"  SUPABASE_URL: {supabase_url}")
    print(f"  SUPABASE_KEY: {'Present' if supabase_key else 'Missing'}")
    exit(1)

print(f"✅ Supabase URL: {supabase_url[:30]}...")
supabase: Client = create_client(supabase_url, supabase_key)

# ============================================
# DATABASE INITIALIZATION
# ============================================
def init_db():
    """
    This function creates tables in Supabase.
    Run this ONCE after setting up your Supabase project.
    You can execute SQL directly in Supabase SQL Editor or use this function.
    """
    try:
        # Insert sample route
        route_data = {
            "route_name": "GITAM to Miyapur",
            "start_point": "GITAM CAMPUS",
            "end_point": "Miyapur",
            "duration": 45
        }
        existing_route = supabase.table('routes').select("*").eq('route_name', 'GITAM to Miyapur').execute()
        if not existing_route.data:
            route_result = supabase.table('routes').insert(route_data).execute()
            route_id = route_result.data[0]['route_id']
        else:
            route_id = existing_route.data[0]['route_id']
        
        # Insert sample bus
        bus_data = {
            "bus_number": "BUS001",
            "capacity": 40,
            "route_id": route_id
        }
        existing_bus = supabase.table('buses').select("*").eq('bus_number', 'BUS001').execute()
        if not existing_bus.data:
            bus_result = supabase.table('buses').insert(bus_data).execute()
            bus_id = bus_result.data[0]['bus_id']
        else:
            bus_id = existing_bus.data[0]['bus_id']
        
        # Add sample schedules for today and tomorrow
        today = datetime.now().date().isoformat()
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        
        schedules = []
        
        for sched in schedules:
            existing = supabase.table('schedules').select("*").eq('bus_id', bus_id).eq('departure_date', sched['departure_date']).eq('departure_time', sched['departure_time']).execute()
            if not existing.data:
                supabase.table('schedules').insert(sched).execute()
        
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    elif 'admin_id' in session:
        return redirect(url_for('admin_panel'))
    return render_template('index.html')

# ============================================
# USER REGISTRATION
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id'].strip()
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        year = int(request.form['year'])
        
        # Validation
        if not all([student_id, name, year, email, phone, password]):
            flash('All fields are required')
            return render_template('register.html')
        
        if '@student.gitam.edu' not in email:
            flash("Please use your college mail id which ends with *@student.gitam.edu*")
            return render_template('register.html')
        
        if len(phone) != 10 or not phone.isdigit():
            flash("Please enter a valid 10-digit phone number")
            return render_template('register.html')
        
        special_chars = "@#$%&*!?"
        if not (any(char.isupper() for char in password) and 
                any(char.isdigit() for char in password) and 
                any(char in special_chars for char in password) and 
                len(password) >= 8):
            flash("Password must contain at least 1 uppercase, 1 digit, 1 special character (@#$%&*!?), and be at least 8 characters long")
            return render_template("register.html")
        
        # Validate Student ID format
        valid = False
        if year in [1, 2, 3]:
            if student_id.isdigit() and len(student_id) == 10:
                if (year == 1 and student_id.startswith("2025")) or \
                   (year == 2 and student_id.startswith("2024")) or \
                   (year == 3 and student_id.startswith("2023")):
                    valid = True
        elif year == 4:
            if re.fullmatch(r"HU22[A-Z]{4}[0-9]{7}", student_id):
                valid = True
        
        if not valid:
            flash("Invalid Student ID format for your year. Please check the rules.")
            return render_template('register.html')
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        try:
            # Check if user exists
            existing = supabase.table('users').select("*").or_(f"student_id.eq.{student_id},email.eq.{email}").execute()
            if existing.data:
                flash('Student ID or email already exists')
                return render_template('register.html')
            
            # Insert user
            user_data = {
                "student_id": student_id,
                "year": year,
                "name": name,
                "email": email,
                "phone": phone,
                "password_hash": password_hash,
                "is_admin": False
            }
            supabase.table('users').insert(user_data).execute()
            
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {e}")
            return render_template('register.html')
    
    return render_template('register.html')

# ============================================
# ADMIN REGISTRATION
# ============================================
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_reg():
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        admin_name = request.form['admin_name']
        admin_password = request.form['admin_password']
        admin_mail = request.form['admin_mail']
        admin_phone = request.form['admin_phone']
        
        special_chars = "@#$%&*!?"
        if not (any(c.isupper() for c in admin_password) and
                any(c.isdigit() for c in admin_password) and
                any(c in special_chars for c in admin_password) and
                len(admin_password) >= 8):
            flash("Password must contain at least 1 uppercase, 1 digit, 1 special character, and be at least 8 characters long")
            return render_template("admin_register.html")
        
        password_hash = generate_password_hash(admin_password)
        
        try:
            # Check if admin exists
            existing = supabase.table('admins').select("*").or_(f"admin_username.eq.{admin_id},admin_email.eq.{admin_mail}").execute()
            if existing.data:
                flash('Admin ID or email already exists')
                return render_template('admin_register.html')
            
            admin_data = {
                "admin_username": admin_id,
                "admin_name": admin_name,
                "admin_email": admin_mail,
                "admin_phone": admin_phone,
                "password_hash": password_hash
            }
            result = supabase.table('admins').insert(admin_data).execute()
            
            # Create default permissions for new admin
            if result.data:
                new_admin_id = result.data[0]['admin_id']
                permissions_data = {
                    "admin_id": new_admin_id,
                    "can_create_schedules": True,
                    "can_edit_schedules": True,
                    "can_delete_schedules": False,
                    "can_manage_buses": True,
                    "can_manage_routes": True,
                    "can_view_all_bookings": True,
                    "can_cancel_bookings": False,
                    "can_manage_admins": False
                }
                supabase.table('admin_permissions').insert(permissions_data).execute()
            
            flash('Registration successful! Please login.')
            return redirect(url_for('admin_login'))
        except Exception as e:
            flash(f'Error: {e}')
            return render_template('admin_register.html')
    
    return render_template('admin_register.html')

# ============================================
# USER LOGIN
# ============================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['student_id'].strip()
        password = request.form['password']
        year = int(request.form['year'])
        captcha_answer = request.form.get('captcha_answer', '')
        
        # Verify CAPTCHA
        if 'captcha_solution' not in session or str(session['captcha_solution']) != captcha_answer:
            flash("❌ Incorrect CAPTCHA. Please try again.")
            return render_template('login.html')
        
        # Validate ID format
        valid = False
        if year in [1, 2, 3]:
            if student_id.isdigit() and len(student_id) == 10:
                if (year == 1 and student_id.startswith("2025")) or \
                   (year == 2 and student_id.startswith("2024")) or \
                   (year == 3 and student_id.startswith("2023")):
                    valid = True
        elif year == 4:
            if re.fullmatch(r"HU22[A-Z]{4}[0-9]{7}", student_id):
                valid = True
        
        if not valid:
            flash("Invalid Student ID format for your year.")
            return render_template('login.html')
        
        try:
            # Get user from database
            result = supabase.table('users').select("*").eq('student_id', student_id).execute()
            
            if result.data and check_password_hash(result.data[0]['password_hash'], password):
                user = result.data[0]
                session['user_id'] = user['user_id']
                session['student_id'] = user['student_id']
                session['year'] = user['year']
                session['name'] = user['name']
                session.pop('captcha_solution', None)  # Clear captcha
                flash("Login successful ✅")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid credentials ❌")
                return render_template('login.html')
        except Exception as e:
            flash(f"Error: {e}")
            return render_template('login.html')
    
    # Generate CAPTCHA for GET request
    import random
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_solution'] = num1 + num2
    session['captcha_question'] = f"{num1} + {num2}"
    
    return render_template('login.html')

# ============================================
# ADMIN LOGIN
# ============================================
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        captcha_answer = request.form.get('captcha_answer', '')
        if 'captcha_solution' not in session or str(session['captcha_solution']) != captcha_answer:
            flash("❌ Incorrect CAPTCHA. Please try again.")
            return render_template('admin_login.html')
        
        try:
            result = supabase.table('admins').select("*").eq('admin_username', username).execute()
            
            if result.data and check_password_hash(result.data[0]['password_hash'], password):
                admin = result.data[0]
                session['admin_id'] = admin['admin_id']
                session['is_admin'] = True
                session['admin_name'] = admin['admin_name']
                session.pop('captcha_solution', None) 
                
                # Log admin login activity
                try:
                    activity_data = {
                        "admin_id": admin['admin_id'],
                        "action_type": "login",
                        "description": f"Admin {admin['admin_name']} logged in"
                    }
                    supabase.table('admin_activity_log').insert(activity_data).execute()
                    
                    # Create session record
                    session_data = {
                        "admin_id": admin['admin_id'],
                        "is_active": True
                    }
                    supabase.table('admin_sessions').insert(session_data).execute()
                except:
                    pass  # Don't fail login if logging fails
                
                flash("Admin login successful ✅")
                return redirect(url_for('admin_panel'))
            else:
                flash("Invalid credentials ❌")
                return render_template('admin_login.html')
        except Exception as e:
            flash(f"Error: {e}")
            return render_template('admin_login.html')
    import random
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_solution'] = num1 + num2
    session['captcha_question'] = f"{num1} + {num2}"
    
    return render_template('admin_login.html')

# ============================================
# DASHBOARD
# ============================================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        today = datetime.now().date().isoformat()
        schedules_result = supabase.table('schedules').select(
            "*, buses(bus_number, capacity, routes(route_name, start_point, end_point))"
        ).gte('departure_date', today).gt('available_seats', 0).order('departure_date').order('departure_time').execute()
        
        schedules = []
        for s in schedules_result.data:
            schedules.append({
                'schedule_id': s['schedule_id'],
                'departure_date': s['departure_date'],
                'departure_time': s['departure_time'],
                'available_seats': s['available_seats'],
                'bus_number': s['buses']['bus_number'],
                'capacity': s['buses']['capacity'],
                'route_name': s['buses']['routes']['route_name'],
                'start_point': s['buses']['routes']['start_point'],
                'end_point': s['buses']['routes']['end_point']
            })
        
        bookings_result = supabase.table('bookings').select(
            "*, schedules(departure_date, departure_time, buses(bus_number, routes(route_name)))"
        ).eq('user_id', session['user_id']).eq('status', 'confirmed').execute()
        
        bookings = []
        for b in bookings_result.data:
            if b['schedules']['departure_date'] >= today:
                bookings.append({
                    'booking_id': b['booking_id'],
                    'seat_number': b['seat_number'],
                    'booking_time': b['booking_time'],
                    'status': b['status'],
                    'departure_date': b['schedules']['departure_date'],
                    'departure_time': b['schedules']['departure_time'],
                    'bus_number': b['schedules']['buses']['bus_number'],
                    'route_name': b['schedules']['buses']['routes']['route_name']
                })
        
        return render_template('dashboard.html', schedules=schedules, bookings=bookings)
    except Exception as e:
        flash(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', schedules=[], bookings=[])

# ============================================
# BOOK SEAT
# ============================================
@app.route('/book/<int:schedule_id>')
def book_seat(schedule_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    
    try:
        # Check existing booking
        existing = supabase.table('bookings').select("*").eq('user_id', session['user_id']).eq('schedule_id', schedule_id).eq('status', 'confirmed').execute()
        
        if existing.data:
            flash('You already have a booking for this schedule')
            return redirect(url_for('dashboard'))
        
        # Get schedule details with nested data
        schedule_result = supabase.table('schedules').select(
            "*, buses(bus_number, capacity, bus_id, routes(route_name, start_point, end_point))"
        ).eq('schedule_id', schedule_id).execute()
        
        if not schedule_result.data or schedule_result.data[0]['available_seats'] <= 0:
            flash('No seats available for this schedule')
            return redirect(url_for('dashboard'))
        
        schedule_raw = schedule_result.data[0]
        
        # Flatten the nested structure for easier template access
        schedule = {
            'schedule_id': schedule_raw['schedule_id'],
            'departure_date': schedule_raw['departure_date'],
            'departure_time': schedule_raw['departure_time'],
            'available_seats': schedule_raw['available_seats'],
            'bus_number': schedule_raw['buses']['bus_number'],
            'capacity': schedule_raw['buses']['capacity'],
            'route_name': schedule_raw['buses']['routes']['route_name'],
            'start_point': schedule_raw['buses']['routes']['start_point'],
            'end_point': schedule_raw['buses']['routes']['end_point']
        }
        
        # Get booked seats
        booked_result = supabase.table('bookings').select("seat_number").eq('schedule_id', schedule_id).eq('status', 'confirmed').execute()
        booked_seat_numbers = [b['seat_number'] for b in booked_result.data]
        
        # if schedule['seat_number'] < 1 or schedule['seat_number'] > schedule['capacity']:
        #     flash(f"Invalid seat number! Please select a seat between 1 and {schedule['capacity']}.")
        #     return redirect(url_for('book_seat', schedule_id=schedule_id))
# else → continue with existing booking logic


        # Generate available seats
        total_seats = schedule['capacity']
        available_seats = [i for i in range(1, total_seats + 1) if i not in booked_seat_numbers]
        
        return render_template('book_seat.html', schedule=schedule, available_seats=available_seats)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for('dashboard'))

# ============================================
# CONFIRM BOOKING
# ============================================
@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    schedule_id = int(request.form['schedule_id'])
    seat_number = int(request.form['seat_number'])
    
    try:
        # Get schedule with bus capacity
        schedule_result = supabase.table('schedules').select("*, buses(capacity)").eq('schedule_id', schedule_id).execute()
        
        if not schedule_result.data:
            flash('Schedule not found')
            return redirect(url_for('dashboard'))
        
        schedule = schedule_result.data[0]
        bus_capacity = schedule['buses']['capacity']
        
        # ✅ VALIDATE SEAT NUMBER IS WITHIN CAPACITY
        if seat_number < 1 or seat_number > bus_capacity:
            flash(f'Invalid seat number! Please select a seat between 1 and {bus_capacity}.')
            return redirect(url_for('book_seat', schedule_id=schedule_id))
        
        # Check if seat is already booked
        existing_seat = supabase.table('bookings').select("*").eq('schedule_id', schedule_id).eq('seat_number', seat_number).eq('status', 'confirmed').execute()
        
        if existing_seat.data or schedule['available_seats'] <= 0:
            flash('Seat no longer available')
            return redirect(url_for('dashboard'))
        
        # Create booking
        booking_data = {
            "user_id": session['user_id'],
            "schedule_id": schedule_id,
            "seat_number": seat_number,
            "status": "confirmed"
        }
        supabase.table('bookings').insert(booking_data).execute()
        
        # Update available seats
        new_available = schedule['available_seats'] - 1
        supabase.table('schedules').update({"available_seats": new_available}).eq('schedule_id', schedule_id).execute()
        
        flash('Booking confirmed successfully! ✅')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for('dashboard'))

# ============================================
# CANCEL BOOKING
# ============================================
@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get booking
        booking_result = supabase.table('bookings').select(
            "*, schedules(departure_date, departure_time)"
        ).eq('booking_id', booking_id).eq('user_id', session['user_id']).execute()
        
        if not booking_result.data:
            flash('Booking not found')
            return redirect(url_for('dashboard'))
        
        booking = booking_result.data[0]
        
        # Check cancellation time (2 minutes after booking for testing)
        booking_time = datetime.fromisoformat(booking['booking_time'].replace('Z', '+00:00'))
        if datetime.now() - booking_time < timedelta(minutes=2):
            flash('Cannot cancel booking less than 2 minutes after booking')
            return redirect(url_for('dashboard'))
        
        # Cancel booking
        supabase.table('bookings').update({"status": "cancelled"}).eq('booking_id', booking_id).execute()
        
        # Free up seat
        schedule = supabase.table('schedules').select("*").eq('schedule_id', booking['schedule_id']).execute().data[0]
        new_available = schedule['available_seats'] + 1
        supabase.table('schedules').update({"available_seats": new_available}).eq('schedule_id', booking['schedule_id']).execute()
        
        flash('Booking cancelled successfully ✅')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for('dashboard'))

# ============================================
# ADMIN PANEL
# ============================================
@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        flash('Unauthorized Access')
        return redirect(url_for('admin_login'))
    
    try:
        today = datetime.now().date().isoformat()
        schedules = supabase.table('schedules').select(
            "*, buses(bus_number, routes(route_name))"
        ).gte('departure_date', today).order('departure_time').execute()
        
        # Count bookings for each schedule and flatten data
        bookings_data = []
        for schedule in schedules.data:
            booking_count = supabase.table('bookings').select("*", count='exact').eq('schedule_id', schedule['schedule_id']).eq('status', 'confirmed').execute()
            bookings_data.append({
                'schedule_id': schedule['schedule_id'],
                'departure_time': schedule['departure_time'],
                'departure_date': schedule['departure_date'],
                'bus_number': schedule['buses']['bus_number'],
                'route_name': schedule['buses']['routes']['route_name'],
                'booked_seats': booking_count.count if booking_count.count else 0,
                'available_seats': schedule['available_seats']
            })
        
        return render_template('admin.html', bookings=bookings_data)
    except Exception as e:
        flash(f"Error: {e}")
        return render_template('admin.html', bookings=[])

# ============================================
# CREATE SCHEDULE
# ============================================
@app.route('/create_slot', methods=['GET', 'POST'])
def create_slot():
    if not session.get('is_admin'):
        flash('Unauthorized Access')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        bus_number = request.form['bus_number']
        departure_date = request.form['departure_date']
        departure_time = request.form['departure_time']
        total_seats = int(request.form['total_seats'])
        
        try:
            # Get bus
            bus_result = supabase.table('buses').select("*").eq('bus_number', bus_number).execute()
            if not bus_result.data:
                flash("Bus not found! Please add the bus first.")
                return render_template('create_schedule.html')
            
            bus = bus_result.data[0]
            if total_seats > bus['capacity']:
                flash(f"Total seats cannot exceed bus capacity ({bus['capacity']})")
                return render_template('create_schedule.html')
            
            # Create schedule with admin tracking
            schedule_data = {
                "bus_id": bus['bus_id'],
                "departure_date": departure_date,
                "departure_time": departure_time,
                "available_seats": total_seats,
                "status": "active",
                "created_by_admin": session['admin_id']
            }
            result = supabase.table('schedules').insert(schedule_data).execute()
            
            # Log activity
            if result.data:
                activity_data = {
                    "admin_id": session['admin_id'],
                    "action_type": "create",
                    "table_name": "schedules",
                    "record_id": result.data[0]['schedule_id'],
                    "description": f"Created schedule for bus {bus_number} on {departure_date} at {departure_time}"
                }
                supabase.table('admin_activity_log').insert(activity_data).execute()
            
            flash('Schedule created successfully ✅')
            return redirect(url_for('admin_panel'))
        except Exception as e:
            flash(f"Error creating schedule: {e}")
            return render_template('create_schedule.html')
    
    return render_template('create_schedule.html')

# ============================================
# MANAGE BUSES
# ============================================
@app.route('/manage_buses')
def manage_buses():
    if not session.get('is_admin'):
        flash('Unauthorized Access')
        return redirect(url_for('admin_login'))
    
    try:
        buses_result = supabase.table('schedules').select(
            "*, buses(bus_number, capacity, routes(route_name))"
        ).order('departure_date').order('departure_time').execute()
        
        # Flatten the data structure
        buses = []
        for b in buses_result.data:
            buses.append({
                'schedule_id': b['schedule_id'],
                'bus_number': b['buses']['bus_number'],
                'route': b['buses']['routes']['route_name'],
                'departure_time': f"{b['departure_date']}T{b['departure_time']}",
                'total_seats': b['buses']['capacity'],
                'available_seats': b['available_seats'],
                'departure_date': b['departure_date']
            })
        
        return render_template('manage_buses.html', buses=buses)
    except Exception as e:
        flash(f"Error: {e}")
        return render_template('manage_buses.html', buses=[])

# ============================================
# CANCEL SCHEDULE
# ============================================
@app.route('/cancel_schedule/<int:schedule_id>', methods=['POST'])
def cancel_schedule(schedule_id):
    if not session.get('is_admin'):
        flash('Unauthorized Access')
        return redirect(url_for('admin_login'))
    
    try:
        supabase.table('schedules').delete().eq('schedule_id', schedule_id).execute()
        flash("Schedule cancelled successfully ✅")
    except Exception as e:
        flash(f"Error cancelling schedule: {e}")
    
    return redirect(url_for('manage_buses'))

# ============================================
# EDIT SCHEDULE
# ============================================
@app.route('/edit_schedule/<int:schedule_id>', methods=['GET', 'POST'])
def edit_schedule(schedule_id):
    if not session.get('is_admin'):
        flash('Unauthorized Access')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        bus_number = request.form['bus_number']
        departure_datetime = request.form['departure_time']
        total_seats = int(request.form['total_seats'])
        
        try:
            # Get bus
            bus_result = supabase.table('buses').select("*").eq('bus_number', bus_number).execute()
            if not bus_result.data:
                flash("Bus not found")
                return redirect(url_for('manage_buses'))
            
            bus = bus_result.data[0]
            departure_date, departure_time = departure_datetime.split("T")
            
            # Update schedule
            update_data = {
                "bus_id": bus['bus_id'],
                "departure_date": departure_date,
                "departure_time": departure_time,
                "available_seats": total_seats,
                "updated_by_admin": session['admin_id']
            }
            supabase.table('schedules').update(update_data).eq('schedule_id', schedule_id).execute()
            
            # Log activity
            activity_data = {
                "admin_id": session['admin_id'],
                "action_type": "update",
                "table_name": "schedules",
                "record_id": schedule_id,
                "description": f"Updated schedule {schedule_id}"
            }
            supabase.table('admin_activity_log').insert(activity_data).execute()
            
            flash("Schedule updated successfully ✅")
            return redirect(url_for('admin_panel'))
        except Exception as e:
            flash(f"Error updating schedule: {e}")
    
    # GET request - load schedule details
    try:
        schedule_result = supabase.table('schedules').select(
            "*, buses(bus_number, routes(route_name))"
        ).eq('schedule_id', schedule_id).execute()
        
        if schedule_result.data:
            s = schedule_result.data[0]
            bus = {
                'schedule_id': s['schedule_id'],
                'bus_number': s['buses']['bus_number'],
                'route': s['buses']['routes']['route_name'],
                'departure_time': f"{s['departure_date']}T{s['departure_time']}",
                'total_seats': s['available_seats']
            }
            return render_template('edit_schedule.html', bus=bus)
        else:
            flash("Schedule not found")
            return redirect(url_for('manage_buses'))
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for('manage_buses'))

# ============================================
# ALL BOOKINGS
# ============================================
@app.route('/all_bookings')
def all_bookings():
    if not session.get('is_admin'):
        flash('Unauthorized Access')
        return redirect(url_for('admin_login'))
    
    try:
        bookings_result = supabase.table('bookings').select(
            "*, users(student_id, name), schedules(departure_date, departure_time, buses(bus_number, routes(route_name)))"
        ).eq('status', 'confirmed').execute()
        
        # Flatten the data structure
        bookings = []
        for b in bookings_result.data:
            bookings.append({
                'booking_id': b['booking_id'],
                'student_id': b['users']['student_id'],
                'name': b['users']['name'],
                'departure_date': b['schedules']['departure_date'],
                'departure_time': b['schedules']['departure_time'],
                'bus_number': b['schedules']['buses']['bus_number'],
                'route_name': b['schedules']['buses']['routes']['route_name'],
                'seat_number': b['seat_number']
            })
        
        # Sort by departure date and time
        bookings.sort(key=lambda x: (x['departure_date'], x['departure_time']))
        
        return render_template('all_bookings.html', bookings=bookings)
    except Exception as e:
        flash(f"Error: {e}")
        return render_template('all_bookings.html', bookings=[])

# ============================================
# TICKET
# ============================================
# ============================================
# VIEW TICKET
# ============================================
@app.route('/view_ticket/<int:booking_id>')
def view_ticket(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get booking details with all related info
        booking_result = supabase.table('bookings').select(
            "*, users(student_id, name, email, phone), schedules(departure_date, departure_time, buses(bus_number, capacity, routes(route_name, start_point, end_point)))"
        ).eq('booking_id', booking_id).eq('user_id', session['user_id']).eq('status', 'confirmed').execute()
        
        if not booking_result.data:
            flash('Booking not found')
            return redirect(url_for('dashboard'))
        
        booking = booking_result.data[0]
        
        # Flatten data for template
        ticket_data = {
            'booking_id': booking['booking_id'],
            'student_id': booking['users']['student_id'],
            'name': booking['users']['name'],
            'email': booking['users']['email'],
            'phone': booking['users']['phone'],
            'seat_number': booking['seat_number'],
            'bus_number': booking['schedules']['buses']['bus_number'],
            'route_name': booking['schedules']['buses']['routes']['route_name'],
            'start_point': booking['schedules']['buses']['routes']['start_point'],
            'end_point': booking['schedules']['buses']['routes']['end_point'],
            'departure_date': booking['schedules']['departure_date'],
            'departure_time': booking['schedules']['departure_time'],
            'booking_time': booking['booking_time']
        }
        
        return render_template('ticket.html', ticket=ticket_data)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for('dashboard'))
# ============================================
# LOGOUT
# ============================================
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('index'))
from flask import render_template_string

@app.route('/jinja_simple')
def jinja_simple():
    return render_template_string("Jinja OK: {{ 2 + 2 }}")

@app.route('/jinja_ext_test')
def jinja_ext_test():
    # this requires base.html to exist in templates/
    return render_template_string("{% extends 'base.html' %}{% block content %}<h1>EXTENDS OK</h1>{% endblock %}")


# ============================================
# RUN APP
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, threaded=True, host='0.0.0.0', port=port)