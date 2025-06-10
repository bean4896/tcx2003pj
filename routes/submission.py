from flask import Blueprint, request, redirect, render_template, session, url_for, flash
from datetime import datetime
from models.assessment import Task
from models.submission import Submission
from services import auto_grade

submission_bp = Blueprint('submission', __name__)

@submission_bp.route('/submissions/')
def view_submissions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    username = session['username']
    role = session['role']
    
    submissions = Submission.get_all_submissions(username, role)
    
    return render_template("submissions.html", 
                         submissions=submissions,
                         username=username,
                         role=role)

@submission_bp.route("/submit/<int:aid>/<int:tid>", methods=['GET', 'POST'])
def submit_task(aid, tid):
    if 'username' not in session or session['role'] != 'student':
        return redirect(url_for('auth.login'))
    
    username = session['username']
    
    # Get task details
    task = Task.get_task_details(aid, tid)
    if not task:
        flash("Task not found", "error")
        return redirect(url_for('assessment.list_assessments'))
    
    # Check if the current task is past due date
    if task['due_date'] and datetime.now() > task['due_date']:
        # Ensure the flash message is specific to this task
        flash(f"This assessment (ID: {tid}) is past the due date, but you can still re-submit.", "warning")
    
    # Get existing submission if any
    existing_submission = Submission.get_existing_submission(username, aid, tid)
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        if not code:
            flash("Code cannot be empty", "error")
            return redirect(url_for('submission.submit_task', aid=aid, tid=tid))
        
        # Enhanced SQL validation for multi-query
        # Ensure each statement ends with semicolon
        statements = [stmt.strip() for stmt in code.split(';') if stmt.strip()]
        validated_code = '; '.join(statements) + ';' if statements else code
        
        # Check for basic SQL structure
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        if not any(keyword in validated_code.upper() for keyword in sql_keywords):
            flash("Please enter valid SQL statement(s)", "error")
            return redirect(url_for('submission.submit_task', aid=aid, tid=tid))
        
        # Basic syntax check for multi-query
        try:
            # Simple validation - check for balanced quotes and basic structure
            quote_count = validated_code.count("'") + validated_code.count('"')
            if quote_count % 2 != 0:
                flash("Unbalanced quotes in SQL code", "error")
                return redirect(url_for('submission.submit_task', aid=aid, tid=tid))
        except:
            pass  # Continue with submission even if validation fails
        
        # Submit or update submission
        if existing_submission:
            success, message = Submission.update_submission(username, aid, tid, validated_code)
        else:
            success, message = Submission.create_submission(username, aid, tid, validated_code)
        
        if not success:
            flash(message, "error")
            return redirect(url_for('submission.submit_task', aid=aid, tid=tid))
        
        # Run auto-grading
        print(f"Starting auto-grading for {username}, aid={aid}, tid={tid}")
        print(f"Code to grade: {validated_code}")
        
        try:
            grading_success = auto_grade(username, aid, tid, validated_code)
            
            if grading_success:
                flash("Code submitted and graded successfully!", "success")
            else:
                flash("Code submitted but auto-grading failed. Manual grading may be required.", "warning")
        except Exception as e:
            print(f"Auto-grading exception: {str(e)}")
            flash("Code submitted but auto-grading encountered an error.", "warning")
        
        return redirect(url_for('assessment.detail', aid=aid))
    
    return render_template("submit_task.html", 
                         task=task, 
                         existing_submission=existing_submission,
                         username=username)
