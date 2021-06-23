from flask import Flask, render_template, request, flash, Markup, jsonify, redirect, url_for, session

from flask_wtf import CSRFProtect

from flask_sqlalchemy import SQLAlchemy

from datetime import date
from dateutil.relativedelta import relativedelta
from werkzeug.utils import secure_filename

from forms import *

import os, random, math, csv

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eMedicInternet.db'
app.config['SQLALCHEMY_BINDS'] = {"intranet":'sqlite:///eMedicIntranet.db'}

db = SQLAlchemy(app)

class MaskedIC(db.Model):
  __tablename__ = "masked_ic"
  uuid = db.Column(db.String(), primary_key=True, unique=True, nullable=False)
  masked_ic = db.Column(db.String(), nullable=False)

class AMPT(db.Model):
  __tablename__ = "ampt"
  uuid = db.Column(db.String(), db.ForeignKey('masked_ic.uuid'), primary_key=True, unique=True, nullable=False)
  ampt_date = db.Column(db.Date(), nullable=False)

class VocDate(db.Model):
  __tablename__ = "voc_date"
  uuid = db.Column(db.String(), db.ForeignKey('masked_ic.uuid'), primary_key=True, unique=True, nullable=False)
  course_date = db.Column(db.Date(), nullable=False)

class AED(db.Model):
  __bind_key__= "intranet"
  __tablename__ = "aed"
  uuid = db.Column(db.String(), db.ForeignKey('masked_ic.uuid'), primary_key=True, unique=True, nullable=False)
  aed_date = db.Column(db.Date(), nullable=False)
  aed_name = db.Column(db.String(), nullable=False)
  aed_cert = db.Column(db.String(), unique=True, nullable=False)

class VocName(db.Model):
  __bind_key__= "intranet"
  __tablename__ = "voc_name"
  uuid = db.Column(db.String(), db.ForeignKey('masked_ic.uuid'), primary_key=True, unique=True, nullable=False)
  course_name = db.Column(db.String(), nullable=False)

class FullName(db.Model):
  __bind_key__= "intranet"
  __tablename__ = "full_name"
  uuid = db.Column(db.String(), db.ForeignKey('masked_ic.uuid'), primary_key=True, unique=True, nullable=False)
  full_name = db.Column(db.String(), nullable=False)

class Profile(db.Model):
  __bind_key__= "intranet"
  __tablename__ = "profile"
  uuid = db.Column(db.String(), db.ForeignKey('masked_ic.uuid'), primary_key=True, unique=True, nullable=False)
  rights = db.Column(db.String(), nullable=False)

# flask routes
@app.route('/')
def index():
  return redirect(url_for('home'))

@app.route('/home', methods=['GET', 'POST'])
def home():
  form = uuidForm()
  if form.validate_on_submit():
    session['uuid'] = form.uuid.data
    return redirect(url_for('medic'))
  return render_template('home.html', form = form)

@app.route('/medic')
def medic():
  medicQuery = (
    db.session.query(MaskedIC, AMPT, VocDate)
    .join(AMPT)
    .join(VocDate)
    .filter_by(uuid=session['uuid'])
    .first())
  ampt = medicQuery.AMPT.ampt_date
  voc = medicQuery.VocDate.course_date
  if ampt == None and voc == None:
    return redirect(url_for('invalid'))
  ic = medicQuery.MaskedIC.masked_ic
  expDate = max(ampt, voc) + relativedelta(years=1)
  duration = (expDate-date.today()).days
  valid = True
  if duration < 0:
    valid = False
    duration *= -1
  return render_template('medic.html', ic = ic, exp = expDate.strftime("%-d %B %Y"), valid = valid, months = math.floor(duration/30.5), days = duration)

@app.route('/inet', methods=['GET', 'POST'])
def inet():
  form = uuidForm()
  if form.validate_on_submit():
    session['uuid'] = form.uuid.data
    return redirect(url_for('unit'))
  return render_template('inet.html', form = form)

@app.route('/unit', methods=['GET', 'POST'])
def unit():
  csvform = csvForm()
  unitform = unitForm(
    entry="Masked NRIC, First Word Of Name"
  )
  if csvform.validate_on_submit():
    f = csvform.file.data
    #try:
    overwrite = unitForm(
      entry=csv.reader(
      f.read().decode("utf-8-sig").split('\n')
      )
    )        
    unitform.populate_obj(overwrite)
    #except:
    #  csvform.file.errors.append("The file is formatted incorrectly")
         
  return render_template('unit.html', inet = True, csvform = csvform, unitform=unitform)

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