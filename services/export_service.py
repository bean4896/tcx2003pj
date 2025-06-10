import pandas as pd
import io
from datetime import datetime
from models.leaderboard import Leaderboard

class ExportService:
    @staticmethod
    def _sanitize_sheet_name(name):
        """Sanitize sheet name for Excel compatibility"""
        sheet_name = name[:31]
        for char in ['\\', '/', '*', '[', ']', ':', '?']:
            sheet_name = sheet_name.replace(char, '_')
        return sheet_name
    
    @staticmethod
    def _format_date(date_obj):
        """Format date object to string"""
        return date_obj.strftime('%Y-%m-%d %H:%M') if date_obj else 'N/A'
    
    @staticmethod
    def _calculate_completion_rate(completed, total):
        """Calculate completion rate percentage"""
        return round((completed / total * 100), 1) if total > 0 else 0
    
    @staticmethod
    def _create_summary_data(assessments):
        """Create summary data for all assessments"""
        summary_data = []
        for assessment in assessments:
            leaderboard = assessment['leaderboard']
            summary_data.append({
                'Assessment Title': assessment['title'],
                'Description': assessment['description'] or 'N/A',
                'Total Tasks': assessment['total_tasks'],
                'Due Date': ExportService._format_date(assessment['due_date']),
                'Participants': len(leaderboard),
                'Highest Score': max([s['total_score'] for s in leaderboard]) if leaderboard else 0,
                'Average Score': round(sum([s['total_score'] for s in leaderboard]) / len(leaderboard), 2) if leaderboard else 0
            })
        return summary_data
    
    @staticmethod
    def _create_leaderboard_data(assessment):
        """Create formatted leaderboard data"""
        leaderboard_data = []
        for student in assessment['leaderboard']:
            completion_rate = ExportService._calculate_completion_rate(
                student['completed_tasks'], 
                assessment['total_tasks']
            )
            last_sub = ExportService._format_date(student['last_submission'])
            
            leaderboard_data.append({
                'Rank': student['rank'],
                'Username': student['username'],
                'Total Score': round(student['total_score'], 2),
                'Average Score': round(student['average_score'], 2),
                'Tasks Completed': student['completed_tasks'],
                'Completion Rate (%)': completion_rate,
                'Last Submission': last_sub
            })
        return leaderboard_data
    
    @staticmethod
    def _create_assessment_info(assessment):
        """Create assessment information section"""
        return [
            ['Assessment Information', ''],
            ['Title', assessment['title']],
            ['Description', assessment['description'] or 'N/A'],
            ['Total Tasks', assessment['total_tasks']],
            ['Due Date', ExportService._format_date(assessment['due_date'])],
            ['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['', ''],
            ['Leaderboard Data', '']
        ]
    
    @staticmethod
    def export_all_leaderboards():
        """Export all leaderboard data to Excel"""
        try:
            assessments = Leaderboard.get_all_assessments_with_leaderboard()
            excel_buffer = io.BytesIO()
            
            if not assessments:
                empty_df = pd.DataFrame({
                    'Message': ['No assessment data available'],
                    'Generated': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                })
                empty_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                excel_buffer.seek(0)
                return excel_buffer
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Create summary sheet
                summary_data = ExportService._create_summary_data(assessments)
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Create individual assessment sheets
                for assessment in assessments:
                    sheet_name = ExportService._sanitize_sheet_name(assessment['title'])
                    
                    if assessment['leaderboard']:
                        # Create leaderboard data
                        leaderboard_data = ExportService._create_leaderboard_data(assessment)
                        info_data = ExportService._create_assessment_info(assessment)
                        
                        # Create DataFrames
                        info_df = pd.DataFrame(info_data, columns=['Field', 'Value'])
                        leaderboard_df = pd.DataFrame(leaderboard_data)
                        
                        # Write to Excel
                        info_df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        startrow = len(info_df) + 1
                        leaderboard_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=startrow)
                    else:
                        # No data sheet
                        no_data_df = pd.DataFrame({
                            'Message': [f'No submissions for: {assessment["title"]}'],
                            'Assessment ID': [assessment['aid']],
                            'Total Tasks': [assessment['total_tasks']]
                        })
                        no_data_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            excel_buffer.seek(0)
            return excel_buffer
            
        except Exception as e:
            print(f"Error in export_all_leaderboards: {e}")
            return ExportService._create_error_workbook(str(e))
    
    @staticmethod
    def export_single_leaderboard(assessment_id):
        """Export single assessment leaderboard to Excel"""
        try:
            assessment = Leaderboard.get_single_assessment_leaderboard(assessment_id)
            
            if not assessment or not assessment['leaderboard']:
                return None
            
            # Create Excel file
            excel_buffer = io.BytesIO()
            leaderboard_data = ExportService._create_leaderboard_data(assessment)
            df = pd.DataFrame(leaderboard_data)
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                sheet_name = ExportService._sanitize_sheet_name(assessment['title'])
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            excel_buffer.seek(0)
            return excel_buffer
            
        except Exception as e:
            print(f"Error in export_single_leaderboard: {e}")
            return None
    
    @staticmethod
    def _create_error_workbook(error_message):
        """Create error workbook"""
        error_df = pd.DataFrame({
            'Error': [f'Export failed: {error_message}'],
            'Time': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        })
        excel_buffer = io.BytesIO()
        error_df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        return excel_buffer
