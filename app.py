from flask import Flask, session, request, redirect
from config import Config
from routes import auth_bp, main_bp, assessment_bp, submission_bp, leaderboard_bp

app = Flask(__name__)
app.config.from_object(Config)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(assessment_bp)
app.register_blueprint(submission_bp)
app.register_blueprint(leaderboard_bp)
@app.before_request
def before_request():
    # Allow access to login and register without requiring a session
    if 'session_id' not in session and request.endpoint not in ['auth.login', 'auth.register']:
        return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
