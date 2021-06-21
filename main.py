from flask import Flask, render_template, request, flash, Markup, jsonify, redirect, url_for, session

from flask_wtf import CSRFProtect

from flask_sqlalchemy import SQLAlchemy

from datetime import date
from dateutil.relativedelta import relativedelta

from forms import *

import os, random, math

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eMedicInternet.db'
app.config['SQLALCHEMY_BINDS'] = {"intranet":'sqlite:///eMedicIntranet.db'}

db = SQLAlchemy(app)

class Medic(db.Model):
  __tablename__ = "maskedIC"
  UUID = db.Column(db.String(), primary_key=True, unique=True, nullable=False)
  maskedIC = db.Column(db.String(), nullable=False)
  ampt = db.relationship("AMPT", backref="medic", lazy='dynamic')
  eligibility = db.relationship("Eligibility", lazy='dynamic')

class AMPT(db.Model):
  __tablename__ = "AMPT"
  UUID = db.Column(db.String(), db.ForeignKey('maskedIC.UUID'), primary_key=True, unique=True, nullable=False)
  Date = db.Column(db.Date(), nullable=False)

class Eligibility(db.Model):
  __tablename__ = "Eligibility"
  UUID = db.Column(db.String(), db.ForeignKey('maskedIC.UUID'), primary_key=True, unique=True, nullable=False)
  Date = db.Column(db.Date(), nullable=False)

class AED(db.Model):
  __bind_key__= "intranet"
  UUID = db.Column(db.String(), db.ForeignKey('maskedIC.UUID'), primary_key=True, unique=True, nullable=False)
  Date = db.Column(db.Date(), nullable=False)

class EligibilityCourse(db.Model):
  __bind_key__= "intranet"
  UUID = db.Column(db.String(), db.ForeignKey('maskedIC.UUID'), primary_key=True, unique=True, nullable=False)
  Course = db.Column(db.String(), nullable=False)

class fullName(db.Model):
  __bind_key__= "intranet"
  UUID = db.Column(db.String(), db.ForeignKey('maskedIC.UUID'), primary_key=True, unique=True, nullable=False)
  Course = db.Column(db.String(), nullable=False)

# flask routes
@app.route('/')
def index():
  return redirect(url_for('home'))

@app.route('/home', methods=['GET', 'POST'])
def home():
  form = uuidForm()
  if form.validate_on_submit():
    session['uuid'] = form.uuid.data
    if Medic.query.filter_by(UUID=session['uuid']).first() == None:
      return redirect(url_for('invalid'))
    return redirect(url_for('medic'))
  return render_template('home.html', form = form)

@app.route('/medic')
def medic():
  MedicQ = Medic.query.filter_by(UUID=session['uuid']).first()
  ampt = MedicQ.ampt.all()[0].Date
  eligibility = MedicQ.eligibility.all()[0].Date
  expDate = max(ampt, eligibility) + relativedelta(years=1)
  duration = (expDate-date.today()).days
  valid = True
  if duration < 0:
    valid = False
    duration *= -1
  return render_template('medic.html', ic = MedicQ.maskedIC, exp = expDate.strftime("%-d %B %Y"), valid = valid, months = math.floor(duration/30.5), days = duration)

@app.route('/inet', methods=['GET', 'POST'])
def inet():
  form = uuidForm()
  if form.validate_on_submit():
    session['uuid'] = form.uuid.data
    #if Medic.query.filter_by(UUID=session['uuid']).first() == None:
    #  return redirect(url_for('invalid'))
    return redirect(url_for('unit'))
  return render_template('inet.html', form = form)

@app.route('/unit')
def unit():
  form = unitForm()
  if form.validate_on_submit():
    if form.search.data:
      return redirect(url_for('unit'))
    elif form.submit.data:
      return redirect(url_for('unit'))
  return render_template('unit.html', inet = True, form = form)

@app.route('/smti')
def smti():
  return render_template('smti.html', inet = True)

@app.route('/invalid')
def invalid():
  return render_template('invalid.html', nodate = True)

@app.route('/terms')
def terms():
  return render_template('terms.html', nodate = True)

@app.errorhandler(404)
def page_not_found(self):
  return render_template('404.html', nodate = True)


if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=random.randint(2000, 9000))