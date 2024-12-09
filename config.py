import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_secure_key'
    SQLALCHEMY_DATABASE_URI = 'mysql://root:root@localhost/seleniumbot'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
