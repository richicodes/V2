from flask import Flask, render_template, request, flash, Markup, jsonify, redirect, url_for, session, send_file

from flask_wtf import CSRFProtect

from pandas import read_excel

from datetime import datetime

from forms import *
from helper import *
from models import *

import os, random, math, csv, io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eMedicInternet.db'
app.config['SQLALCHEMY_BINDS'] = {"intranet":'sqlite:///eMedicIntranet.db'}

db.init_app(app)
csrf = CSRFProtect(app)

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
  if medicQuery == None:
    return redirect(url_for('invalid'))
  else:    
    ampt = multi_getattr(medicQuery,"AMPT.ampt_date", None)
    voc = multi_getattr(medicQuery,"VocDate.course_date", None)
    validity, expDate, duration = expiryCalculator(ampt, voc)
  if validity == "Invalid" :
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
    entry='"Masked NRIC (123X)","FULL NAME"'
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
          MaskedIC.query.
          filter(MaskedIC.masked_ic==query[0]).
          all()
        )

        for uuid in [result.uuid for result in ICQuery]:
          NameQuery = (
            FullName.query.
            filter(FullName.uuid==uuid)
            .filter(FullName.full_name==query[1])        
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
      formsearch.submitunit.errors.append("No search query detected in input field. Click 'Upload' to populate input field with file.")
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
          MaskedIC.query.
          filter(MaskedIC.masked_ic==query[0]).
          all()
        )

        for uuid in [result.uuid for result in ICQuery]:
          NameQuery = (
            FullName.query.
            filter(FullName.uuid==uuid)
            .filter(FullName.full_name==query[1])        
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
      formsearch.submit_smti.errors.append("No search query detected in input field. Click 'Upload' to populate input field with file.")
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
          MaskedIC.query.
          filter(MaskedIC.masked_ic==query[0]).
          all()
        )

        for uuid in [result.uuid for result in ICQuery]:
          NameQuery = (
            FullName.query.
            filter(FullName.uuid==uuid)
            .filter(FullName.full_name==query[1])        
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
      formsearchp.submit_profile.errors.append("No search query detected in input field. Click 'Upload' to populate input field with file.")
    except:
      formsearchp.submit_profile.errors.append("The query is formatted incorrectly")
  
  if formsearchp.download_profile.data and formsearchp.validate():
    session['tab'] = "profile"
    return sendExcel(
      dict_in=session['result'], 
      column_order=["masked_ic", "full_name", "rights"],
      filename_suffix="profiles"
      )

  if formsearchp.modify_profile.data and formsearchp.validate():
    session['tab'] = "profile"
    q = formsearchp.entry_profile.data.splitlines()
    ''' class EmptyQuery(Exception):
      """Exception raised when query is empty"""
      pass

    class QueryError(Exception):
      """Exception raised when there is an query error"""
      pass

    try:
      queries = list(csv.reader(q, quotechar='"', quoting=csv.QUOTE_ALL))
      session['result_p'] = []
      error= ""

      print(queries)

      if len(queries) == 1:
        raise EmptyQuery()

      if not "uuid" in queries[0]:
        error.append("UUID must be included")
        raise QueryError() 

      for query in queries:

        query = dict(zip(queries[0], query))

        for column, value in query:
          if value == "":
            del query[column]

        if(
            FullName.query.filter(FullName.uuid==query["uuid"]) == None or
            MaskedIC.query.filter(MaskedIC.uuid==query["uuid"]) == None
          ) and not (
            "masked_ic" in query and 
            "full_name" in query
          ):

          error.append(query["uuid"] + " does not exist. Create entry by defining 'masked_ic and 'full_name'")
        
        else:
          for column, value in query:
            if value == "#DEL":  '''


    session["modal"] = "Test Modal"
    print(session["modal"])

      


        
        
        
        
        
        
    ''' except EmptyQuery:
      formsearchp.submit_profile.errors.append("No modify query detected in input field. Click 'Upload' to populate input field with file.")

    except QueryError:
      formsearchp.submit_profile.errors.append("Query Error")

    except:
      formsearchp.submit_profile.errors.append("The query is formatted incorrectly") '''
         
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