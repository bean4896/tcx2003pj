# models/user.py
import hashlib
import mysql.connector
from datetime import datetime
from models.database import get_db_connection

#@staticmethod is used to define methods that do not require an instance of the class to be called.
class User:
    @staticmethod
    def create_user(username, password):
        """Create a new user account"""
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            conn.commit()
            return True, "Account created successfully"
        except mysql.connector.Error as err:
            return False, "Username already exists"
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def authenticate(username, password):
        """Authenticate user login"""
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT password, role FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            
            if result and result['password'] == hashed_password:
                return True, result
            return False, None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_user_details(username):
        """Get user details"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update_password(username, new_password):
        """Update user password"""
        hashed_password = hashlib.md5(new_password.encode()).hexdigest()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (hashed_password, username)
            )
            conn.commit()
            return True
        except:
            return False
        finally:
            cursor.close()
            conn.close()

class Session:
    @staticmethod
    def create_session(session_id, username):
        """Create a new session record"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            start_time = datetime.now()
            cursor.execute(
                "INSERT INTO sessions (session_num, username, start_at) VALUES (%s, %s, %s)",
                (session_id, username, start_time)
            )
            conn.commit()
            return start_time
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def end_session(session_id):
        """End a session by updating end_at time"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            end_time = datetime.now()
            cursor.execute(
                "UPDATE sessions SET end_at = %s WHERE session_num = %s",
                (end_time, session_id)
            )
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_user_sessions(username):
        """Get all sessions for a user"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                "SELECT session_num, start_at, end_at FROM sessions WHERE username = %s ORDER BY start_at DESC",
                (username,)
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
