from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_migrate import Migrate
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import numpy as np
from threading import Thread
import schedule
import time
from Google import connect_to_google_sheets


app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
migrate = Migrate(app, db) 
login = LoginManager(app)
login.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(128))

class UserSelenium(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platforma = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)

class Zadatak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platforma = db.Column(db.String(150), nullable=False)
    link = db.Column(db.String(300), nullable=False)
    komentar_na_koji_odgovaramo = db.Column(db.Text, nullable=False)
    komentar = db.Column(db.Text, nullable=False)
    komentarisano = db.Column(db.Boolean, default=False)

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    zadaci = Zadatak.query.all()
    zapisi = [
        {
            'platforma': zadatak.platforma,
            'link': zadatak.link,
            'komentar_na_koji_odgovaramo': zadatak.komentar_na_koji_odgovaramo,
            'komentar': zadatak.komentar,
            'komentarisano': zadatak.komentarisano
        }
        for zadatak in zadaci
    ]
    
    return render_template('dashboard.html', zapisi=zapisi)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username is None or password is None:
            flash('Molimo unesite ponovo vaš username i password', 'danger')
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Pogrešan username ili password', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def provjeri_google_sheets():
    sheet1, sheet2 = connect_to_google_sheets()
    
    headers = sheet1[0]
    
    for row in sheet1[1:]:  
        row_dict = dict(zip(headers, row))  #
        
        if not Zadatak.query.filter_by(link=row_dict['link']).first():
            zadatak = Zadatak(platforma=row_dict['platforma'], link=row_dict['link'], 
                               komentar_na_koji_odgovaramo=row_dict['komentar_na_koji_odgovaramo'], komentar=row_dict['komentar'], komentarisano=False)
            db.session.add(zadatak)
            db.session.commit()

    pokreni_zadatak()

def pokreni_zadatak():
    tasks = Zadatak.query.filter_by(komentarisano=False).all()
    users = UserSelenium.query.all()

    chrome_options = Options()
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome()

    for task in tasks:
        if task.platforma == 'klix.ba':
            for user in users:
                if user.platforma == 'klix.ba' and user.is_active == True:
                    username = user.username
                    password = user.password
                    break

            try:
                driver.get('https://klix.ba')
                time.sleep(3)
                driver.maximize_window()

                sviButtoni = driver.find_elements(By.TAG_NAME, 'button')
                button = driver.find_element(By.ID, 'user')
                time.sleep(3)
                button.click()
                time.sleep(3)

                inputUsername = driver.find_element(By.NAME, "username")
                inputPassword = driver.find_element(By.ID, "lpassword")

                inputUsername.send_keys(username)
                inputPassword.send_keys(password)

                for button in sviButtoni:
                    if "prijavise" in button.text.lower().replace(" ", ""):
                        button.click()
                        break
                time.sleep(3)

                driver.get(task.link)

                sviAElementi = driver.find_elements(By.TAG_NAME, 'a')

                for AElemenat in sviAElementi:
                    if 'prikaži sve komentare' in AElemenat.text.lower():
                        AElemenat.click()
                        time.sleep(3)
                        break

                if task.komentar_na_koji_odgovaramo == "":
                    komentarInput = driver.find_element(By.ID, 'komentarinput')
                    komentarInput.send_keys(task.komentar)
                    time.sleep(3)
                    sviButtoni = driver.find_elements(By.TAG_NAME, 'button')

                    for button in sviButtoni:
                        if 'objavi komentar' in button.text.lower():
                            print("UŠAO SAM U OBJAVI KOMENTAR")
                            button.click()
                            task.komentarisano = True
                            break

                else:
                    time.sleep(2)
                    komentar_sekcija = driver.find_element(By.CLASS_NAME, 'comments_display')
                    komentari = komentar_sekcija.find_elements(By.CLASS_NAME, 'komentar')
                    for komentar in komentari:
                        unutrasnji_divovi = komentar.find_elements(By.XPATH, './div')
                        if len(unutrasnji_divovi) > 1:
                            text_div = unutrasnji_divovi[1]
                            text_div_unutrasnji_divovi = text_div.find_elements(By.XPATH, './div')
                            trazeni_div = text_div_unutrasnji_divovi[0]
                            trazeni_div_tekst = trazeni_div.find_elements(By.TAG_NAME, 'div')
                            text = trazeni_div_tekst[0].text
                            print(text)
                            print("--------------------")
                            print(task.komentar_na_koji_odgovaramo)

                        if text == task.komentar_na_koji_odgovaramo:
                            print("RADI SVE KONACNOOO!!!!!")
                            sviButtoni = driver.find_elements(By.TAG_NAME, 'button')

                            for button in sviButtoni:
                                if 'odgovori' in button.text.lower():
                                    button.click()
                                    task.komentarisano = True
                                    break
                            komentarInput = driver.find_elements(By.ID, 'komentarinput')
                            komentarInput[1].send_keys(task.komentar)
                            submit_button = komentar_sekcija.find_elements(By.CSS_SELECTOR, 'button[type="submit"]')
                            submit_button[1].click()
                            time.sleep(3)

                db.session.commit()
                
            finally:
                driver.quit()
        elif task.platforma == "facebook.com":
            pass
            ''' for user in users:
                if user.platforma == 'facebook.com' and user.is_active == True:
                    username = user.username
                    password = user.password
                    break
            while True:
                driver = webdriver.Chrome()
                driver.get('https://facebook.com')
                time.sleep(3)
                driver.maximize_window()

                inputUsername = driver.find_element(By.ID, "email")
                inputPassword = driver.find_element(By.ID, "pass")  

                inputUsername.send_keys(username)
                inputPassword.send_keys(password)  

                sviButtoni = driver.find_elements(By.TAG_NAME, 'button')
                for button in sviButtoni:
                    if 'log in' in button.text.lower():
                        button.click()
                        break
                time.sleep(3)

                driver.get(task.link)

                if task.komentar_na_koji_odgovaramo == "":
                    p_element = driver.find_element(By.CSS_SELECTOR, 'p.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xdpxx8g')
                    span_element = p_element.find_element(By.CSS_SELECTOR, 'span[data-lexical-text="true"]')
                    span_element.send_keys(task.komentar)
                    time.sleep(5) '''
    driver.quit()  


@app.route('/manual-check', methods=['POST'])
@login_required
def manual_check():
    provjeri_google_sheets()  
    flash('Provjera CSV fajla pokrenuta ručno.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)


