from app import app, db
from model import User, Company, Flight
from werkzeug.security import generate_password_hash

with app.app_context():
    db.drop_all()  # очищаем старую БД (если есть)
    db.create_all()  # создаём таблицы заново

    # Admin
    admin = User(username="admin", password=generate_password_hash("12345678"), role="admin")
    db.session.add(admin)

    # Manager
    manager = User(username="manager1", password=generate_password_hash("1234567"), role="manager")
    db.session.add(manager)
    company = Company(name="AirFrance", manager_id=manager.id)
    db.session.add(company)

    # User
    user = User(username="elina", password=generate_password_hash("7"), role="user")
    db.session.add(user)

    # Рейсы
    flight1 = Flight(company_id=company.id, origin="Moscow", destination="Paris", date="2025-10-10", price=300, seats=50)
    flight2 = Flight(company_id=company.id, origin="Paris", destination="Moscow", date="2025-10-05", price=250, seats=30)
    db.session.add_all([flight1, flight2])

    db.session.commit()
    print("Тестовые данные добавлены! Логин/пароль для всех: elina/manager1/admin / 1234567")