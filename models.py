from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin,RoleMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db=SQLAlchemy()


user_roles = db.Table('user_roles',
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                      db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
                      )


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # Renamed from password_hash to password
    active = db.Column(db.Boolean, default=True)
    fs_uniquifier = db.Column(db.String(128))
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy=True))
    books = db.relationship('Book', backref='user', lazy=True)
    book_counts = db.Column(db.Integer, default=0)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)  # Changed password_hash to password

    def check_password(self, password):
        return check_password_hash(self.password, password)  


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_name = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)  # Added author field
    description = db.Column(db.Text, nullable=False)     # Added description field
    content = db.Column(db.Text, nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    due_date = db.Column(db.DateTime, nullable=True)  # Nullable as not all books may have due dates
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_approved = db.Column(db.Boolean, default=False)  
    is_requested = db.Column(db.Boolean, default=False)

    @property
    def rating(self):
        total_votes = self.likes + self.dislikes
        return (self.likes / total_votes) * 100 if total_votes > 0 else 0



class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True)
    description = db.Column(db.String(256))


class Section(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    section_name=db.Column(db.String(100),unique=True,nullable=False)
    date_created=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    description=db.Column(db.Text,nullable=False)
    books=db.relationship('Book',backref='section',lazy=True,cascade='all,delete-orphan')
