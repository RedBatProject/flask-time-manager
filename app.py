# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import secrets
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timemanager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Task(db.Model):
    __tablename__ = 'tasks'  # Explicitly naming the table
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    time_allocation = db.Column(db.Integer)  # Time in minutes
    start_time = db.Column(db.Time)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class Goal(db.Model):
    __tablename__ = 'goals'  # Explicitly naming the table
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    target_date = db.Column(db.DateTime)
    progress = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='in_progress')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_db():
    """Initialize the database and create tables"""
    with app.app_context():
        # Check if database needs to be initialized
        db_path = os.path.join('instance', 'timemanager.db')
        if not os.path.exists(db_path):
            db.create_all()
            print("Database initialized!")
        else:
            # Attempt to create any new tables/columns without dropping existing ones
            try:
                db.create_all()
                print("Database schema updated!")
            except Exception as e:
                print(f"Database already exists, error: {e}")

@app.route('/')
def index():
    today = datetime.utcnow().date()
    
    # Use try-except to handle potential database errors
    try:
        today_tasks = Task.query.filter_by(date=today).order_by(Task.start_time).all()
        upcoming_tasks = Task.query.filter(
            Task.date > today
        ).order_by(Task.date, Task.start_time).limit(5).all()
        
        total_time = sum(task.time_allocation for task in today_tasks if task.time_allocation)
        hours = total_time // 60
        minutes = total_time % 60
        
    except Exception as e:
        flash(f'Database error: {str(e)}', 'danger')
        today_tasks = []
        upcoming_tasks = []
        hours = 0
        minutes = 0
    
    return render_template('index.html', 
                         today_tasks=today_tasks,
                         upcoming_tasks=upcoming_tasks,
                         total_time_hours=hours,
                         total_time_minutes=minutes,
                         today=today)

@app.route('/add_task', methods=['POST'])
def add_task():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        time_allocation = request.form.get('time_allocation')
        start_time_str = request.form.get('start_time')
        
        # Convert string inputs to proper datetime objects
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time() if start_time_str else None
        
        task = Task(
            title=title,
            description=description,
            date=date,
            time_allocation=int(time_allocation) if time_allocation else None,
            start_time=start_time
        )
        
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback the transaction on error
        flash(f'Error adding task: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/complete_task/<int:id>')
def complete_task(id):
    try:
        task = Task.query.get_or_404(id)
        task.status = 'completed'
        db.session.commit()
        flash('Task marked as complete!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing task: {str(e)}', 'danger')
    return redirect(url_for('index'))

@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    print("Initialized the database.")

if __name__ == '__main__':
    init_db()  # Initialize database before running the app
    app.run(debug=True)

