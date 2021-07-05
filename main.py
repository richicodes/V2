from flask import Flask, render_template, request, flash, Markup, jsonify, redirect, url_for, session, send_file

from flask_wtf import CSRFProtect

from flask_sqlalchemy import SQLAlchemy

from pandas import read_excel

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
  uuid = db.Column(db.String(), db.ForeignKey('full_name.uuid'), primary_key=True, unique=True, nullable=False)
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
  formxls = unitXlsxForm()
  formsearch = unitSearchForm(
    entry='"Masked NRIC (123X)","FIRSTWORDOFNAME"'
  )
  if 'result' not in session:
    session['result'] = None

  if formxls.submitxls.data and formxls.validate():
    f = formxls.file.data
    try:
      formsearch.entry.data = read_excel(f).to_csv(quoting=csv.QUOTE_ALL, index=False)
    except:
      formxls.file.errors.append("The file is formatted incorrectly")

  if formsearch.submitunit.data and formsearch.validate():
    
    q = formsearch.entry.data.splitlines()
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

        if len(uuids) > 0:
          for uuid in uuids:
            InternetQuery = (
              db.session.query(MaskedIC, AMPT, VocDate)
              .join(AMPT)
              .join(VocDate)
              .filter(MaskedIC.uuid==uuid)
              .first()
            )

            if InternetQuery == None:
              session['result'].append({
                "masked_ic": query[0],
                "first_name": query[1],
                "validity": "Invalid",
                "expiry_date": "Invalid",
                "duration": "Invalid" 
              })
            else:
              validity, expDate, duration = expiryCalculator(
                date1=multi_getattr(InternetQuery, "VocDate.course_date", None),
                date2=multi_getattr(InternetQuery, "AMPT.ampt_date", None)
              )

              session['result'].append({
                "masked_ic": query[0],
                "first_name": query[1],
                "validity": validity,
                "expiry_date": multi_getattr(expDate, 'strftime')("%Y-%m-%d"),
                "duration": duration
                }) 

        else:
          session['result'].append({
            "masked_ic": query[0],
            "first_name": query[1],
            "validity": "Invalid",
            "expiry_date": "Invalid",
            "duration": "Invalid" 
          })

    except EmptyQuery:
      formsearch.submitunit.errors.append("No search query detected in search field. Click 'Upload' to populate search field with file.")
      print("error")
    except:
      formsearch.submitunit.errors.append("The query is formatted incorrectly")
  
  if formsearch.downloadunit.data and formsearch.validate():
    return sendExcel(
      dict_in=session['result'], 
      column_order=["masked_ic", "first_name", "validity", "expiry_date", "duration"], 
      filename_suffix="eMedic"
      )
         
  return render_template('unit.html', inet = True, formxls = formxls, formsearch=formsearch)

@app.route('/smti', methods=['GET', 'POST'])
def smti():
  formxls = smtiXlsxForm()
  formsearch = smtiSearchForm(
    entry_smti='"Masked NRIC (123X)","FULL NAME"'
  )

  formxlsp = profileXlsxForm()
  formsearchp = profileSearchForm(
    entry_profile='"Masked NRIC (123X)","FULL NAME"'
  )

  if 'result' not in session:
    session['result'] = None

  if 'result_p' not in session:
    session['result_p'] = None

  if 'tab' not in session:
    session['tab'] = "smti"

  if formxls.submitxls_smti.data and formxls.validate():
    session['tab'] = "smti"
    f = formxls.file_smti.data
    try:
      formsearch.entry_smti.data = read_excel(f).to_csv(quoting=csv.QUOTE_ALL, index=False)
    except:
      formxls.file_smti.errors.append("The file is formatted incorrectly")

  if formsearch.submit_smti.data and formsearch.validate():
    session['tab'] = "smti"

    q = formsearch.entry_smti.data.splitlines()
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
            db.session.query(FullName)
            .filter(FullName.uuid==uuid)
            .filter(FullName.full_name == query[1])
            .all()
          )
          uuids += [result.uuid for result in NameQuery]

        if len(uuids) > 0:
          for uuid in uuids:
            InternetQuery = (
              db.session.query(MaskedIC, AMPT, VocDate)
              .join(AMPT)
              .join(VocDate)
              .filter(MaskedIC.uuid==uuid)
              .first()
            )

            IntranetQuery = (
              db.session.query(FullName, VocName, AED)
              .join(VocName)
              .join(AED)
              .filter(FullName.uuid==uuid)
              .first()
            )

            if InternetQuery == None and IntranetQuery == None:
              session['result'].append({
              "masked_ic": query[0],
              "full_name": query[1],
              "validity":   "Invalid",
              "expiry_date": "Invalid",
              "duration": "Invalid",
              "course_name": "Invalid",
              "course_date": "Invalid",
              "ampt_date": "Invalid",
              "aed_name": "Invalid",
              "aed_date": "Invalid",
              "aed_cert": "Invalid"
              }) 
            else:
              validity, expDate, duration = expiryCalculator(
                date1=multi_getattr(InternetQuery, "VocDate.course_date", None),
                date2=multi_getattr(InternetQuery, "AMPT.ampt_date", None)
              )
              session['result'].append({
              "masked_ic": query[0],
              "full_name": query[1],
              "validity": validity,
              "expiry_date": multi_getattr(expDate,"strftime")("%Y-%m-%d"),
              "duration": duration,
              "course_name": multi_getattr(IntranetQuery,"VocName.course_name"),
              "course_date": multi_getattr(InternetQuery,"VocDate.course_date.strftime")("%Y-%m-%d"),
              "ampt_date": multi_getattr(InternetQuery,"AMPT.ampt_date.strftime")("%Y-%m-%d"),
              "aed_name": multi_getattr(IntranetQuery,"AED.aed_name"),
              "aed_date": multi_getattr(IntranetQuery,"AED.aed_date.strftime")("%Y-%m-%d"),
              "aed_cert": multi_getattr(IntranetQuery,"AED.aed_cert")
              }) 
        else:
          session['result'].append({
            "masked_ic": query[0],
            "full_name": query[1],
            "validity":   "Invalid",
            "expiry_date": "Invalid",
            "duration": "Invalid",
            "course_name": "Invalid",
            "course_date": "Invalid",
            "ampt_date": "Invalid",
            "aed_name": "Invalid",
            "aed_date": "Invalid",
            "aed_cert": "Invalid"
            })
          print(vars(session))

    except EmptyQuery:
      formsearch.submit_smti.errors.append("No search query detected in search field. Click 'Upload' to populate search field with file.")
    except:
      formsearch.submit_smti.errors.append("The query is formatted incorrectly")
  
  if formsearch.download_smti.data and formsearch.validate():
    session['tab'] = "smti"
    return sendExcel(
      dict_in=session['result'], 
      column_order=["masked_ic", "full_name", "validity", "expiry_date", "duration", "course_name", "course_date", "ampt_date", "aed_cert"], 
      filename_suffix="eMedic"
      )

  if formxlsp.submitxls_profile.data and formxlsp.validate():
    session['tab'] = "profile"
    f = formxlsp.file_profile.data
    try:
      formsearchp.entry_profile.data = read_excel(f).to_csv(quoting=csv.QUOTE_ALL, index=False)
    except:
      formxlsp.file.errors.append("The file is formatted incorrectly")

  if formsearchp.submit_profile.data and formsearchp.validate():
    session['tab'] = "profile"
    q = formsearchp.entry_profile.data.splitlines()
    class EmptyQuery(Exception):
      """Exception raised when query is empty"""
      pass

    try:
      queries = list(csv.reader(q, quotechar='"', quoting=csv.QUOTE_ALL))
      session['result_p'] = []

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
            db.session.query(FullName)
            .filter(FullName.uuid==uuid)
            .filter(FullName.full_name == query[1])
            .all()
          )
          uuids += [result.uuid for result in NameQuery]

        if len(uuids) > 0:
          for uuid in uuids:
            IntranetQuery = (
              db.session.query(FullName, Profile)
              .join(Profile)
              .filter(FullName.uuid==uuid)
              .first()
            )

            if IntranetQuery == None:
              session['result_p'].append({
                "masked_ic": query[0],
                "full_name": query[1],
                "rights": "Invalid" 
              })
            
            else:
              session['result_p'].append({
              "masked_ic": query[0],
              "full_name": query[1],
              "rights": multi_getattr(IntranetQuery, "Profile.rights")
              }) 
        else:
          session['result_p'].append({
            "masked_ic": query[0],
            "full_name": query[1],
            "rights": "Invalid" 
          })

    except EmptyQuery:
      formsearchp.submit_profile.errors.append("No search query detected in search field. Click 'Upload' to populate search field with file.")
    except:
      formsearchp.submit_profile.errors.append("The query is formatted incorrectly")
  
  if formsearchp.download_profile.data and formsearchp.validate():
    session['tab'] = "profile"
    return sendExcel(
      dict_in=session['result'], 
      column_order=["masked_ic", "full_name", "rights"],
      filename_suffix="profiles"
      )
         
  return render_template('smti.html', inet = True, formxls = formxls, formsearch=formsearch, formxlsp = formxlsp, formsearchp=formsearchp)


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