# routes/main.py
from flask import Blueprint, render_template, session, redirect, url_for
from models import Session

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    if 'session_id' in session:
        return redirect("/home")
    return redirect("/login")

@main_bp.route("/home")
def home():
    if 'username' not in session:
        return redirect("/login")
    
    username = session['username']
    activity_history = Session.get_user_sessions(username)
    
    return render_template("home.html", 
                         username=username, 
                         activity_history=activity_history)


@main_bp.route('/assessments')
def assessments():
    return redirect(url_for('assessment.list_assessments'))

@main_bp.route('/submissions')
def submissions():
    return redirect(url_for('submission.view_submissions'))