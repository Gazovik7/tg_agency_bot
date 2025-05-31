import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/monitoring_db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models  # noqa: F401
    db.create_all()

# Import routes after app initialization
from routes import *  # noqa: F401, F403

# Start integrated Telegram monitoring
try:
    from integrated_monitor import start_telegram_monitoring
    import threading
    import time
    
    def delayed_start():
        time.sleep(3)  # Wait for app to fully initialize
        start_telegram_monitoring()
    
    monitor_thread = threading.Thread(target=delayed_start, daemon=True)
    monitor_thread.start()
    logging.info("Telegram мониторинг запущен в фоновом режиме")
except Exception as e:
    logging.error(f"Ошибка запуска Telegram мониторинга: {e}")
