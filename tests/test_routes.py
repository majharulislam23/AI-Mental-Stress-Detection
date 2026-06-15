import pytest
from app import create_app
from models import db

class TestConfig:
    SECRET_KEY = 'test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    return app.test_client()

def register_login(client):
    client.post('/register', data={'name':'Test User','email':'test@example.com','password':'password123'}, follow_redirects=True)

def test_register_login_routes(client):
    r = client.post('/register', data={'name':'Test User','email':'test@example.com','password':'password123'}, follow_redirects=True)
    assert b'Dashboard' in r.data or b'Hello' in r.data
    client.get('/logout')
    r = client.post('/login', data={'email':'test@example.com','password':'password123'}, follow_redirects=True)
    assert b'Dashboard' in r.data or b'Hello' in r.data

def test_stress_submission_result(client):
    register_login(client)
    r = client.post('/stress-test', data={'feeling_text':'I feel anxious about exams','mood':'anxious','sleep_quality':'4','pressure_level':'8','anxiety_level':'8'}, follow_redirects=True)
    assert b'Stress Questionnaire' in r.data
    answers = {f'q{i}':'4' for i in range(5)}
    r = client.post('/questionnaire', data=answers, follow_redirects=True)
    assert b'analyzing' in r.data.lower() or b'AI is analyzing' in r.data
