from flask import Flask
from flask_login import LoginManager,login_required,current_user,UserMixin,login_user, logout_user, login_required
from flask_security import Security
from models import db,User
from datastorefile import datastore
import secrets
from worker import celery_init_app
from sample_data import initialize_sample_data
import flask_excel as excel
from celery.schedules import crontab
from tasks import monthly_reminder,daily_remainder
from cache import cache
###Create the app instance

def create_app():
    app=Flask(__name__)

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'  # Specify the login view

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))



    app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///appdb.sqlite3'
    app.config['SECRET_KEY']=secrets.token_hex(16)
    app.config['SECURITY_PASSWORD_SALT']='thisnameispriyansh'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
    app.config['WTF_CSR_ENABLED']=False
    app.config['SECURITY_TOKEN_AUTHENTICATION_HEADER'] = 'Authentication-Token'
    app.config['CACHE_TYPE']='RedisCache'
    app.config['CACHE_REDIS_HOST']='localhost'
    app.config['CACHE_REDIS_PORT'] = 6379
    app.config['CACHE_REDIS_DB']=3
    app.config['CACHE_DEFAULT_TIMEOUT']=300
    cache.init_app(app)
    db.init_app(app)
    
    excel.init_excel(app)
    app.security=Security(app,datastore)
    with app.app_context():
        import views
    return app


app=create_app()
celery_app=celery_init_app(app)



@celery_app.on_after_configure.connect
def celery_job(sender,**kwargs):
    #sender.add_periodic_task(crontab(hour=8, minute=0, day_of_month=1), monthly_reminder.s())
    #sender.add_periodic_task(crontab(hour=18, minute=0), daily_reminder.s())

    #for testing
    sender.add_periodic_task(60,monthly_reminder.s())
    sender.add_periodic_task(40,daily_remainder.s())



if __name__=='__main__':
    initialize_sample_data()
    app.run(debug=True)
