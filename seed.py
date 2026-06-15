from app import create_app
from models import db, WellnessTip, User

app = create_app()

tips = [
    ('Breathing Exercise','Calm','Try 4-4-6 breathing for three minutes to reduce physical tension.','🫁'),
    ('Meditation','Mindfulness','Sit quietly, notice your breath, and gently return when your mind wanders.','🧘'),
    ('Sleep Improvement','Sleep','Keep a fixed sleep time and reduce bright screens before bed.','🌙'),
    ('Time Management','Productivity','Write three priority tasks and start with the smallest one.','⏱️'),
    ('Study/Work Breaks','Focus','Use 25-minute focus blocks followed by 5-minute breaks.','📚'),
    ('Talk to Someone','Support','Share your feelings with a trusted friend, family member, mentor, or counselor.','🤝'),
]

with app.app_context():
    db.create_all()
    if WellnessTip.query.count() == 0:
        for title, category, content, icon in tips:
            db.session.add(WellnessTip(title=title, category=category, content=content, icon=icon))
    if not User.query.filter_by(email='demo@example.com').first():
        demo = User(name='Demo Student', email='demo@example.com', occupation='Student')
        demo.set_password('password123')
        db.session.add(demo)
    db.session.commit()
    print('Database seeded. Demo login: demo@example.com / password123')
