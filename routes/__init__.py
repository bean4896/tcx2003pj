# routes/__init__.py
from .auth import auth_bp
from .main import main_bp
from .assessment import assessment_bp
from .submission import submission_bp
from .leaderboard import leaderboard_bp

__all__ = ['auth_bp', 'main_bp', 'assessment_bp', 'submission_bp', 'leaderboard_bp']
