from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from model import db   # модель у тебя в model.py

# импортируем все роуты
from routers.auth import auth_bp
from routers.user import user_bp
from routers.company import company_bp
from routers.admin import admin_bp

app = Flask(__name__)

# Конфигурация
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "secret-key"  # поменяй потом на свой

# Инициализация
db.init_app(app)
jwt = JWTManager(app)

# Подключаем blueprints (API)
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(company_bp, url_prefix="/company")
app.register_blueprint(admin_bp, url_prefix="/admin")

# HTML-страницы (GET-роуты)
@app.route("/")
def home_page():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/company")
def company_page():
    return render_template("company.html")

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

# Создание БД
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)