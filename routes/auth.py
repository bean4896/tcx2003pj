from flask import Blueprint, request, redirect, render_template, session, url_for, flash
from models.user import User, Session
from uuid import uuid4

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/")
def index():
    if 'session_id' in session:
        return redirect(url_for('auth.home'))
    return redirect(url_for('auth.login'))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        success, user_data = User.authenticate(username, password)  # Fix: unpack the tuple
        if success:
            session_id = str(uuid4())  # Generate session ID
            start_time = Session.create_session(session_id, username)  # Fix: pass session_id first
            session['session_id'] = session_id
            session['username'] = username
            session['role'] = user_data['role']
            session['login_time'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
            
            return redirect(url_for('auth.home'))
        else:
            return render_template("login.html", error="Invalid username or password")
    
    registration_success = session.pop('registration_success', None)
    return render_template("login.html", registration_success=registration_success)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        success, message = User.create_user(username, password)  # Fix: use static method
        if success:
            session['registration_success'] = f"Account for {username} created successfully! Please log in."
            return redirect(url_for('auth.login'))
        else:
            return render_template("register.html", error=message)
    
    return render_template("register.html")

@auth_bp.route("/home")
def home():
    if 'username' in session:
        username = session['username']
        activity_history = Session.get_user_sessions(username)
        return render_template("home.html", username=username, activity_history=activity_history)
    else:
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout', methods=['POST'])
def logout():
    if 'session_id' in session:
        Session.end_session(session['session_id'])
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/account', methods=['GET', 'POST'])
def account():
    if 'username' in session:
        username = session['username']
        role = session['role']
        user_details = User.get_user_details(username)
        
        if request.method == "POST":
            new_password = request.form['new_password']
            if User.update_password(username, new_password):
                flash("Password changed successfully!", "success")
        
        return render_template("account.html", username=username, role=role, user_details=user_details)
    else:
        return redirect(url_for('auth.login'))
