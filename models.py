from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    occupation = db.Column(db.String(120), nullable=True)
    preferred_theme = db.Column(db.String(30), default='calm')
    notifications = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stress_tests = db.relationship('StressTest', backref='user', lazy=True, cascade='all, delete-orphan')
    chats = db.relationship('ChatMessage', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class StressTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    sleep_quality = db.Column(db.Integer, nullable=False)
    pressure_level = db.Column(db.Integer, nullable=False)
    anxiety_level = db.Column(db.Integer, nullable=False)
    feeling_text = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String(50), nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    factors = db.Column(db.Text, nullable=False)
    recommendations = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    answers = db.relationship('QuestionnaireAnswer', backref='stress_test', lazy=True, cascade='all, delete-orphan')
    report = db.relationship('Report', backref='stress_test', lazy=True, uselist=False, cascade='all, delete-orphan')

class QuestionnaireAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stress_test_id = db.Column(db.Integer, db.ForeignKey('stress_test.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)
    answer_value = db.Column(db.Integer, nullable=False)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stress_test_id = db.Column(db.Integer, db.ForeignKey('stress_test.id'), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    emotional_pattern = db.Column(db.Text, nullable=False)
    sleep_pressure_analysis = db.Column(db.Text, nullable=False)
    risk_indicator = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WellnessTip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(20), default='🌿')
