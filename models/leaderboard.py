from models.database import get_db_connection
import mysql.connector
from mysql.connector import Error

class Leaderboard:
    @staticmethod
    def get_all_assessments_with_leaderboard():
        """Get all assessments with their leaderboard data using optimized single query"""
        connection = get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
            WITH assessment_stats AS (
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
            ),
            ranked_students AS (
                SELECT 
                    g.aid,
                    g.username,
                    SUM(g.score) as total_score,
                    COUNT(g.tid) as completed_tasks,
                    ROUND(AVG(g.score), 2) as average_score,
                    MAX(g.graded_at) as last_submission,
                    ROW_NUMBER() OVER (PARTITION BY g.aid ORDER BY SUM(g.score) DESC, MAX(g.graded_at) ASC) as student_rank
                FROM grades g
                JOIN users u ON g.username = u.username
                WHERE u.role = 'student'
                GROUP BY g.aid, g.username
            )
            SELECT 
                a.*,
                r.username,
                r.total_score,
                r.completed_tasks,
                r.average_score,
                r.last_submission,
                r.student_rank
            FROM assessment_stats a
            LEFT JOIN ranked_students r ON a.aid = r.aid AND r.student_rank <= 10
            ORDER BY a.created_at DESC, r.student_rank ASC
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Group by assessment efficiently
            assessments = {}
            for row in results:
                aid = row['aid']
                
                if aid not in assessments:
                    assessments[aid] = {
                        'aid': aid,
                        'title': row['title'],
                        'description': row['description'],
                        'due_date': row['due_date'],
                        'created_at': row['created_at'],
                        'total_tasks': row['total_tasks'],
                        'leaderboard': []
                    }
                
                if row['username']:
                    assessments[aid]['leaderboard'].append({
                        'rank': row['student_rank'],
                        'username': row['username'],
                        'total_score': float(row['total_score']),
                        'completed_tasks': row['completed_tasks'],
                        'average_score': float(row['average_score']),
                        'last_submission': row['last_submission']
                    })
            
            return list(assessments.values())
            
        except Error as e:
            print(f"Error fetching leaderboard data: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    @staticmethod
    def get_single_assessment_leaderboard(assessment_id):
        """Get single assessment leaderboard data"""
        connection = get_db_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
            WITH assessment_info AS (
                SELECT 
                    a.aid,
                    a.title,
                    a.description,
                    a.due_date,
                    COUNT(DISTINCT t.tid) as total_tasks
                FROM assessments a
                LEFT JOIN tasks t ON a.aid = t.aid
                WHERE a.aid = %s
                GROUP BY a.aid
            ),
            student_scores AS (
                SELECT 
                    g.username,
                    SUM(g.score) as total_score,
                    AVG(g.score) as average_score,
                    COUNT(g.tid) as completed_tasks,
                    MAX(g.graded_at) as last_submission
                FROM grades g
                JOIN users u ON g.username = u.username
                WHERE g.aid = %s AND u.role = 'student'
                GROUP BY g.username
                HAVING COUNT(g.tid) > 0
                ORDER BY total_score DESC, average_score DESC, last_submission ASC
            )
            SELECT 
                a.*,
                s.username,
                s.total_score,
                s.average_score,
                s.completed_tasks,
                s.last_submission,
                ROW_NUMBER() OVER (ORDER BY s.total_score DESC, s.average_score DESC, s.last_submission ASC) as `rank`
            FROM assessment_info a
            LEFT JOIN student_scores s ON 1=1
            """
            
            cursor.execute(query, (assessment_id, assessment_id))
            results = cursor.fetchall()
            
            if not results or not results[0]['aid']:
                return None
            
            # Build assessment data
            assessment = {
                'aid': results[0]['aid'],
                'title': results[0]['title'],
                'description': results[0]['description'],
                'due_date': results[0]['due_date'],
                'total_tasks': results[0]['total_tasks'],
                'leaderboard': []
            }
            
            for row in results:
                if row['username']:
                    assessment['leaderboard'].append({
                        'rank': row['rank'],
                        'username': row['username'],
                        'total_score': float(row['total_score']),
                        'average_score': float(row['average_score']),
                        'completed_tasks': row['completed_tasks'],
                        'last_submission': row['last_submission']
                    })
            
            return assessment
            
        except Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
