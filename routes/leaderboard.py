from flask import Blueprint, render_template, send_file, flash, redirect, url_for, request
from models.leaderboard import Leaderboard
from services.export_service import ExportService
from datetime import datetime

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/leaderboard')
def leaderboard():
    """Main leaderboard page showing all assessments"""
    assessments = Leaderboard.get_all_assessments_with_leaderboard()
    return render_template('leaderboard.html', assessments=assessments)

@leaderboard_bp.route('/leaderboard/export')
def export_leaderboard():
    """Export all leaderboard data to Excel"""
    try:
        excel_buffer = ExportService.export_all_leaderboards()
        
        if excel_buffer:
            filename = f"all_leaderboards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return send_file(
                excel_buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('No data available to export', 'warning')
            return redirect(url_for('leaderboard.leaderboard'))
            
    except Exception as e:
        print(f"Error in export route: {e}")
        flash('An error occurred while exporting data', 'error')
        return redirect(url_for('leaderboard.leaderboard'))

@leaderboard_bp.route('/leaderboard/export/<int:assessment_id>')
def export_single_assessment(assessment_id):
    """Export single assessment leaderboard to Excel"""
    try:
        excel_buffer = ExportService.export_single_leaderboard(assessment_id)
        
        if excel_buffer:
            filename = f"assessment_{assessment_id}_leaderboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return send_file(
                excel_buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('No data available to export for this assessment', 'warning')
            return redirect(url_for('leaderboard.leaderboard'))
            
    except Exception as e:
        print(f"Error in single export route: {e}")
        flash('An error occurred while exporting data', 'error')
        return redirect(url_for('leaderboard.leaderboard'))
