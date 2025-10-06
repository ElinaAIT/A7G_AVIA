from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")  # user / manager / admin
    blocked = db.Column(db.Boolean, default=False)  # поле для блокировки пользователя

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    encrypted_password = db.Column(db.String(500), nullable=True)
    is_admin_created = db.Column(db.Boolean, default=False)
    blocked = db.Column(db.Boolean, default=False)  # блокировка компании

class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    date = db.Column(db.String(100))
    price = db.Column(db.Float)
    seats = db.Column(db.Integer)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'))
    status = db.Column(db.String(20), default="paid")  # paid / refunded / canceled
