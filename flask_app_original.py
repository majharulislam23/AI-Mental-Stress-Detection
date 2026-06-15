from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from config import Config
from models import db, User, StressTest, QuestionnaireAnswer, Report, ChatMessage, WellnessTip
from stress_algorithm import QUESTIONS, calculate_stress_score, generate_insights, chatbot_reply


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    def current_user():
        uid = session.get('user_id')
        return User.query.get(uid) if uid else None

    @app.context_processor
    def inject_user():
        return {'current_user': current_user(), 'questions': QUESTIONS}

    @app.route('/')
    def landing():
        return render_template('landing.html')

    @app.route('/onboarding')
    def onboarding():
        return render_template('onboarding.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            name = request.form['name'].strip()
            email = request.form['email'].strip().lower()
            password = request.form['password']
            if User.query.filter_by(email=email).first():
                flash('This email is already registered.', 'danger')
                return redirect(url_for('register'))
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            flash('Account created successfully.', 'success')
            return redirect(url_for('dashboard'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email'].strip().lower()
            password = request.form['password']
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                flash('Welcome back.', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid email or password.', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('landing'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user = current_user()
        latest = StressTest.query.filter_by(user_id=user.id).order_by(StressTest.created_at.desc()).first()
        recent = StressTest.query.filter_by(user_id=user.id).order_by(StressTest.created_at.desc()).limit(5).all()
        quote = 'Small pauses protect big dreams.'
        return render_template('dashboard.html', latest=latest, recent=recent, quote=quote)

    @app.route('/stress-test', methods=['GET', 'POST'])
    @login_required
    def stress_test():
        if request.method == 'POST':
            form_data = {
                'feeling_text': request.form.get('feeling_text', ''),
                'mood': request.form.get('mood', 'okay'),
                'sleep_quality': int(request.form.get('sleep_quality', 5)),
                'pressure_level': int(request.form.get('pressure_level', 5)),
                'anxiety_level': int(request.form.get('anxiety_level', 5))
            }
            session['stress_input'] = form_data
            return redirect(url_for('questionnaire'))
        return render_template('stress_input.html')

    @app.route('/questionnaire', methods=['GET', 'POST'])
    @login_required
    def questionnaire():
        if 'stress_input' not in session:
            return redirect(url_for('stress_test'))
        if request.method == 'POST':
            values = [int(request.form.get(f'q{i}', 3)) for i in range(len(QUESTIONS))]
            data = session['stress_input']
            score = calculate_stress_score(data['mood'], data['sleep_quality'], data['pressure_level'], data['anxiety_level'], values, data['feeling_text'])
            insights = generate_insights(score, data['mood'], data['sleep_quality'], data['pressure_level'], data['anxiety_level'], values, data['feeling_text'])
            test = StressTest(
                user_id=session['user_id'], mood=data['mood'], sleep_quality=data['sleep_quality'],
                pressure_level=data['pressure_level'], anxiety_level=data['anxiety_level'], feeling_text=data['feeling_text'],
                score=score, level=insights['level'], explanation=insights['explanation'],
                factors='|'.join(insights['factors']), recommendations='|'.join(insights['recommendations'])
            )
            db.session.add(test)
            db.session.flush()
            for q, v in zip(QUESTIONS, values):
                db.session.add(QuestionnaireAnswer(stress_test_id=test.id, question=q, answer_value=v))
            risk = 'Low' if score <= 39 else 'Medium' if score <= 69 else 'High'
            report = Report(
                stress_test_id=test.id,
                summary=f'Your stress level is {insights["level"]} with a score of {score}%.',
                emotional_pattern=f'Mood is {data["mood"]}; anxiety level is {data["anxiety_level"]}/10.',
                sleep_pressure_analysis=f'Sleep quality is {data["sleep_quality"]}/10 and pressure level is {data["pressure_level"]}/10.',
                risk_indicator=risk
            )
            db.session.add(report)
            db.session.commit()
            session.pop('stress_input', None)
            return redirect(url_for('analysis_loading', test_id=test.id))
        return render_template('questionnaire.html', questions=QUESTIONS)

    @app.route('/analysis/<int:test_id>')
    @login_required
    def analysis_loading(test_id):
        return render_template('analysis.html', test_id=test_id)

    @app.route('/result/<int:test_id>')
    @login_required
    def result(test_id):
        test = StressTest.query.get_or_404(test_id)
        if test.user_id != session['user_id']:
            return redirect(url_for('dashboard'))
        return render_template('result.html', test=test, factors=test.factors.split('|'), recommendations=test.recommendations.split('|'))


    @app.route('/reports')
    @login_required
    def reports():
        tests = StressTest.query.filter_by(user_id=session['user_id']).order_by(StressTest.created_at.desc()).all()
        return render_template('reports.html', tests=tests)

    @app.route('/report/<int:test_id>')
    @login_required
    def report(test_id):
        test = StressTest.query.get_or_404(test_id)
        if test.user_id != session['user_id']:
            return redirect(url_for('dashboard'))
        return render_template('report.html', test=test, report=test.report, factors=test.factors.split('|'), recommendations=test.recommendations.split('|'))

    @app.route('/report/<int:test_id>/download')
    @login_required
    def download_report(test_id):
        test = StressTest.query.get_or_404(test_id)
        if test.user_id != session['user_id']:
            return redirect(url_for('dashboard'))
        content = f"AI Mental Stress Detector Report\nScore: {test.score}%\nLevel: {test.level}\nExplanation: {test.explanation}\nFactors: {test.factors.replace('|', ', ')}\nRecommendations: {test.recommendations.replace('|', '; ')}"
        response = make_response(content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename=stress_report_{test.id}.txt'
        return response

    @app.route('/history')
    @login_required
    def history():
        tests = StressTest.query.filter_by(user_id=session['user_id']).order_by(StressTest.created_at.desc()).all()
        labels = [t.created_at.strftime('%d %b') for t in reversed(tests[-10:])]
        scores = [t.score for t in reversed(tests[-10:])]
        return render_template('history.html', tests=tests, labels=labels, scores=scores)

    @app.route('/wellness-tips')
    @login_required
    def wellness_tips():
        tips = WellnessTip.query.all()
        return render_template('wellness.html', tips=tips)

    @app.route('/assistant', methods=['GET', 'POST'])
    @login_required
    def assistant():
        if request.method == 'POST':
            msg = request.form.get('message', '').strip()
            if msg:
                db.session.add(ChatMessage(user_id=session['user_id'], sender='user', message=msg))
                reply = chatbot_reply(msg)
                db.session.add(ChatMessage(user_id=session['user_id'], sender='bot', message=reply))
                db.session.commit()
            return redirect(url_for('assistant'))
        messages = ChatMessage.query.filter_by(user_id=session['user_id']).order_by(ChatMessage.created_at.asc()).all()
        return render_template('assistant.html', messages=messages)

    @app.route('/api/chat', methods=['POST'])
    @login_required
    def api_chat():
        msg = request.json.get('message', '')
        reply = chatbot_reply(msg)
        db.session.add(ChatMessage(user_id=session['user_id'], sender='user', message=msg))
        db.session.add(ChatMessage(user_id=session['user_id'], sender='bot', message=reply))
        db.session.commit()
        return jsonify({'reply': reply})

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        user = current_user()
        if request.method == 'POST':
            user.name = request.form.get('name', user.name)
            user.age = request.form.get('age') or None
            user.occupation = request.form.get('occupation')
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('profile'))
        return render_template('profile.html', user=user)

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        user = current_user()
        if request.method == 'POST':
            user.preferred_theme = request.form.get('theme', 'calm')
            user.notifications = bool(request.form.get('notifications'))
            db.session.commit()
            flash('Settings saved.', 'success')
            return redirect(url_for('settings'))
        return render_template('settings.html', user=user)

    @app.route('/emergency')
    def emergency():
        return render_template('emergency.html')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
