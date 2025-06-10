from models.database import get_db_connection
from datetime import datetime
from mysql.connector import Error
class Assessment:
    @staticmethod
    def get_all_assessments(username=None, role='student'):
        """Get all active assessments"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            if role == 'student':
                cursor.execute("""
                    SELECT 
                        a.aid,
                        a.title,
                        a.description,
                        a.due_date,
                        a.created_at,
                        COUNT(DISTINCT t.tid) as total_tasks,
                        COUNT(DISTINCT s.tid) as submitted_tasks
                    FROM assessments a
                    LEFT JOIN tasks t ON a.aid = t.aid
                    LEFT JOIN submissions s ON t.tid = s.tid AND t.aid = s.aid AND s.username = %s
                    WHERE a.is_active = TRUE
                    GROUP BY a.aid
                    ORDER BY a.due_date ASC
                """, (username,))
            else:  # teacher view
                cursor.execute("""
                    SELECT 
                        a.aid,
                        a.title,
                        a.description,
                        a.due_date,
                        a.created_at,
                        COUNT(DISTINCT t.tid) as total_tasks
                    FROM assessments a
                    LEFT JOIN tasks t ON a.aid = t.aid
                    WHERE a.is_active = TRUE
                    GROUP BY a.aid
                    ORDER BY a.due_date ASC
                """)
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_assessment_by_id(aid):
        """Get assessment details by ID"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM assessments WHERE aid = %s AND is_active = TRUE
            """, (aid,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_due_date(aid, new_due_date):
        """Update assessment due date"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if new_due_date is None:
                cursor.execute("""
                    UPDATE assessments 
                    SET due_date = NULL 
                    WHERE aid = %s
                """, (aid,))
            else:
                # Convert datetime string to MySQL format
                due_date_obj = datetime.strptime(new_due_date, '%Y-%m-%dT%H:%M')
                formatted_date = due_date_obj.strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute("""
                    UPDATE assessments 
                    SET due_date = %s 
                    WHERE aid = %s
                """, (formatted_date, aid))
            
            conn.commit()
            return cursor.rowcount > 0
        except Error as e: # type: ignore
            print(f"Database error: {e}")
            return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()        
    
    @staticmethod
    def get_assessment_tasks(aid, username=None, role='student'):
        """Get tasks for an assessment"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            if role == 'student':
                cursor.execute("""
                    SELECT 
                        t.tid,
                        t.title,
                        t.description,
                        t.max_score,
                        s.code,
                        s.submit_at,
                        g.score,
                        g.feedback
                    FROM tasks t
                    LEFT JOIN submissions s ON t.tid = s.tid AND t.aid = s.aid AND s.username = %s
                    LEFT JOIN grades g ON t.tid = g.tid AND t.aid = g.aid AND g.username = %s
                    WHERE t.aid = %s
                    ORDER BY t.tid
                """, (username, username, aid))
            else:  # teacher view
                cursor.execute("""
                    SELECT 
                        t.tid,
                        t.title,
                        t.description,
                        t.max_score,
                        COUNT(DISTINCT s.username) as submission_count
                    FROM tasks t
                    LEFT JOIN submissions s ON t.tid = s.tid AND t.aid = s.aid
                    WHERE t.aid = %s
                    GROUP BY t.tid
                    ORDER BY t.tid
                """, (aid,))
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def is_submission_late(aid, submission_time=None):
        """Check if a submission is late based on assessment due date"""
        if submission_time is None:
            submission_time = datetime.now()
        
        assessment = Assessment.get_assessment_by_id(aid)
        if not assessment or not assessment['due_date']:
            return False  # No due date set, so not late
        
        due_date = assessment['due_date']
        if isinstance(due_date, str):
            due_date = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
        
        return submission_time > due_date
    
    @staticmethod
    def get_time_past_due(aid, submission_time=None):
        """Get how much time has passed since assessment due date"""
        if submission_time is None:
            submission_time = datetime.now()
        
        assessment = Assessment.get_assessment_by_id(aid)
        if not assessment or not assessment['due_date']:
            return None
        
        due_date = assessment['due_date']
        if isinstance(due_date, str):
            due_date = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
        
        if submission_time > due_date:
            return submission_time - due_date
        return None
    


class Task:
    @staticmethod
    def get_task_details(aid, tid):
        """Get task details with assessment info"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT t.*, a.title as assessment_title, a.due_date
                FROM tasks t
                JOIN assessments a ON t.aid = a.aid
                WHERE t.tid = %s AND t.aid = %s AND a.is_active = TRUE
            """, (tid, aid))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
