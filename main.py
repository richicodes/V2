from flask import Flask, render_template, request, flash, Markup, jsonify, redirect, url_for, session, send_file

from flask_wtf import CSRFProtect

from flask_sqlalchemy import SQLAlchemy

from pandas import read_excel, DataFrame, ExcelWriter

from datetime import datetime

from forms import *
from helper import *

import os, random, math, csv, io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eMedicInternet.db'
app.config['SQLALCHEMY_BINDS'] = {"intranet":'sqlite:///eMedicIntranet.db'}

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

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
  uuid = db.Column(db.String(), db.ForeignKey('full_name.uuid'), primary_key=True, unique=True, nullable=False)
  aed_date = db.Column(db.Date(), nullable=False)
  aed_name = db.Column(db.String(), nullable=False)
  aed_cert = db.Column(db.String(), unique=True, nullable=False)

class VocName(db.Model):
  __bind_key__= "intranet"
  __tablename__ = "voc_name"
  uuid = db.Column(db.String(), primary_key=True, unique=True, nullable=False)
  course_name = db.Column(db.String(), nullable=False)

class FullName(db.Model):
  __bind_key__= "intranet"
  __tablename__ = "full_name"
  uuid = db.Column(db.String(), primary_key=True, unique=True, nullable=False)
  full_name = db.Column(db.String(), nullable=False)

class Profile(db.Model):
  __bind_key__= "intranet"
  __tablename__ = "profile"
  uuid = db.Column(db.String(), db.ForeignKey('full_name.uuid'), primary_key=True, unique=True, nullable=False)
  rights = db.Column(db.String(), nullable=False)

db.create_all()


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
    .filter(MaskedIC.uuid==session['uuid'])
    .first())
  ampt = medicQuery.AMPT.ampt_date
  voc = medicQuery.VocDate.course_date
  validity, expDate, duration = expiryCalculator(ampt, voc)
  if validity == None:
    return redirect(url_for('invalid'))
  if not validity :
    duration *= -1
  ic = medicQuery.MaskedIC.masked_ic
  return render_template('medic.html', ic = ic, exp = expDate.strftime("%-d %B %Y"), valid = validity, months = math.floor(duration/30.5), days = duration)

@app.route('/inet', methods=['GET', 'POST'])
def inet():
  form = uuidForm()
  if form.validate_on_submit():
    session['uuid'] = form.uuid.data
    return redirect(url_for('unit'))
  return render_template('inet.html', form = form)

@app.route('/unit', methods=['GET', 'POST'])
def unit():
  formxls = xlsForm()
  formunit = unitForm(
    entry='"Masked NRIC (123X)","FIRSTWORDOFNAME"'
  )

  if formxls.submitxls.data and formxls.validate():
    f = formxls.file.data
    try:
      formunit.entry.data = read_excel(f).to_csv(quoting=csv.QUOTE_ALL, index=False)
    except:
      formxls.file.errors.append("The file is formatted incorrectly")

  if formunit.submitunit.data and formunit.validate():
    
    q = formunit.entry.data.splitlines()
    class EmptyQuery(Exception):
      """Exception raised when query is empty"""
      pass

    try:
      queries = list(csv.reader(q, quotechar='"', quoting=csv.QUOTE_ALL))
      session['result'] = []

      print(queries)

      if len(queries) == 1:
        raise EmptyQuery()

      for query in queries[1:]:
        uuids = []
        ICQuery = (
          db.session.query(MaskedIC).
          filter(MaskedIC.masked_ic==query[0]).
          all()
        )

        for uuid in [result.uuid for result in ICQuery]:
          NameQuery = (
            db.session.query(FullName).
            filter(FullName.uuid==uuid)
            .filter(
              (FullName.full_name.startswith(query[1]+" ")) |
              (FullName.full_name==query[1])
            )        
            .all()
          )
          uuids += [result.uuid for result in NameQuery]

        if len(uuids) == 0:
          output.append({
            "masked_ic": query[0],
            "first_name": query[1],
            "validity": False,
            "expiry_date": "Invalid",
            "duration": "Invalid" 
          })
        else:
          for uuid in uuids:
            InternetQuery = (
              db.session.query(MaskedIC, AMPT, VocDate)
              .join(AMPT)
              .join(VocDate)
              .filter(MaskedIC.uuid==uuid)
              .first()
            )
            validity, expDate, duration = expiryCalculator(InternetQuery.VocDate.course_date, InternetQuery.AMPT.ampt_date)
            session['result'].append({
            "masked_ic": query[0],
            "first_name": query[1],
            "validity": validity,
            "expiry_date": expDate.strftime("%Y-%m-%d"),
            "duration": duration
            }) 

    except EmptyQuery:
      formunit.submitunit.errors.append("There is no query detected")
      print("error")
    except:
      formunit.submitunit.errors.append("The query is formatted incorrectly")
  
  if formunit.downloadunit.data and formunit.validate():
    return redirect(url_for('unitdownload'))
         
  return render_template('unit.html', inet = True, formxls = formxls, formunit=formunit, table = session['result'])

@app.route('/smti')
def smti():
  return render_template('smti.html', inet = True)

@app.route('/unit/download', methods=['GET', 'POST'])
def unitdownload():
  print("pass")
  print(session['result'])
  output = io.BytesIO()
  columns= ["masked_ic", "first_name", "validity", "expiry_date", "duration"]
  df=DataFrame.from_dict(session['result'])[columns]
  print(df)
  with ExcelWriter(output) as writer:      
    df.to_excel(writer)
  
  with open("output.xlsx", "wb") as file:
    file.write(output.getbuffer())

  return send_file(output, 
    as_attachment=True,
    download_name="result.xlsx"
  )


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