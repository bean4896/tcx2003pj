from flask import Blueprint, jsonify, render_template, session, redirect, url_for, flash, request
from datetime import datetime
from models.assessment import Assessment
from services.auto_grader import get_grader

assessment_bp = Blueprint('assessment', __name__)

@assessment_bp.route('/assessments/')
@assessment_bp.route('/assessments/list')
def list_assessments():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    username = session['username']
    role = session['role']
    
    assessments = Assessment.get_all_assessments(username, role)
    
    return render_template("assessments.html", 
                        assessments=assessments, 
                        username=username, 
                        role=role,
                        datetime=datetime)

@assessment_bp.route('/assessment/<int:aid>')
def detail(aid):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    username = session['username']
    role = session['role']
    
    assessment = Assessment.get_assessment_by_id(aid)
    if not assessment:
        flash("Assessment not found", "error")
        return redirect(url_for('assessment.list_assessments'))
    
    # Add is_overdue flag to assessment
    assessment['is_overdue'] = Assessment.is_submission_late(aid)
    
    tasks = Assessment.get_assessment_tasks(aid, username, role)
    
    return render_template("assessment_detail.html", 
                         assessment=assessment, 
                         tasks=tasks,
                         username=username,
                         role=role)

@assessment_bp.route('/assessment/<int:aid>/update_due_date', methods=['POST'])
def update_due_date(aid):
    if 'username' not in session or session.get('role') != 'teacher':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        remove_due_date = request.form.get('remove_due_date') == 'on'
        new_due_date = None if remove_due_date else request.form.get('due_date')
        
        if not remove_due_date and not new_due_date:
            flash('Please provide a valid due date', 'danger')
            return redirect(url_for('assessment.detail', aid=aid))
        
        # Update due date
        if Assessment.update_due_date(aid, new_due_date):
            # Trigger re-grade for all submissions
            grader = get_grader()
            re_grade_results = grader.re_grade_after_due_date_change(aid)
            
            flash('Due date updated and grades recalculated', 'success')
        else:
            flash('Failed to update due date', 'danger')
            
    except Exception as e:
        flash(f'Error updating due date: {str(e)}', 'danger')
    
    return redirect(url_for('assessment.detail', aid=aid))

@assessment_bp.route('/assessment/<int:aid>/re_grade', methods=['POST'])
def trigger_re_grade(aid):
    if 'username' not in session or session.get('role') != 'teacher':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        grader = get_grader()
        results = grader.re_grade_after_due_date_change(aid)
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
