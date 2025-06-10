from models.database import get_db_connection
from datetime import datetime
import mysql.connector

class Submission:
    @staticmethod
    def get_existing_submission(username, aid, tid):
        """Get existing submission for a task"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM submissions 
                WHERE username = %s AND aid = %s AND tid = %s
            """, (username, aid, tid))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def create_submission(username, aid, tid, code):
        """Create new submission"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            submit_time = datetime.now()
            cursor.execute("""
                INSERT INTO submissions (username, aid, tid, code, submit_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, aid, tid, code, submit_time))
            conn.commit()
            return True, "Submission created successfully"
        except mysql.connector.Error as err:
            conn.rollback()
            return False, f"Database error: {str(err)}"
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update_submission(username, aid, tid, code):
        """Update existing submission"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            submit_time = datetime.now()
            cursor.execute("""
                UPDATE submissions 
                SET code = %s, submit_at = %s
                WHERE username = %s AND aid = %s AND tid = %s
            """, (code, submit_time, username, aid, tid))
            conn.commit()
            return True, "Submission updated successfully"
        except mysql.connector.Error as err:
            conn.rollback()
            return False, f"Database error: {str(err)}"
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all_submissions(username=None, role='student'):
        """Get submissions based on user role"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            if role == 'student':
                # Show student's own submissions
                cursor.execute("""
                    SELECT 
                        s.*,
                        a.title as assessment_title,
                        t.title as task_title,
                        g.score,
                        g.feedback,
                        g.graded_at
                    FROM submissions s
                    JOIN assessments a ON s.aid = a.aid
                    JOIN tasks t ON s.tid = t.tid AND s.aid = t.aid
                    LEFT JOIN grades g ON s.username = g.username AND s.aid = g.aid AND s.tid = g.tid
                    WHERE s.username = %s
                    ORDER BY s.submit_at DESC
                """, (username,))
            else:  # teacher
                # Show all submissions
                cursor.execute("""
                    SELECT 
                        s.*,
                        a.title as assessment_title,
                        t.title as task_title,
                        g.score,
                        g.feedback,
                        g.graded_at
                    FROM submissions s
                    JOIN assessments a ON s.aid = a.aid
                    JOIN tasks t ON s.tid = t.tid AND s.aid = t.aid
                    LEFT JOIN grades g ON s.username = g.username AND s.aid = g.aid AND s.tid = g.tid
                    ORDER BY s.submit_at DESC
                """)
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
