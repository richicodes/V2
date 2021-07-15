from flask import Flask, render_template, request, flash, Markup, jsonify, redirect, url_for, session, send_file

from flask_wtf import CSRFProtect

from pandas import read_excel

from datetime import datetime

from forms import *
from helper import *
from models import *

import os, random, math, csv, io, re

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
    .filter(MaskedIC.uuid==session['uuid'])
    .join(AMPT)
    .join(VocDate)    
    .first())
  try:
    ampt = medicQuery.AMPT.ampt_date
    voc = medicQuery.VocDate.course_date
    validity, expDate, duration = expiryCalculator(ampt, voc)
  except:
    return redirect(url_for('invalid'))
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

      uuids = []

      for query in queries[1:]:
        query_uuids = []

        dateDict = {}


        ICQuery = (
          MaskedIC.query.
          filter(MaskedIC.masked_ic==query[0]).
          all()
        )

        for uuid in [result.uuid for result in ICQuery]:
          NameQuery = (
            FullName.query
            .filter(FullName.uuid==uuid)
            .filter(FullName.full_name==query[1])        
            .all()
          )
          query_uuids = [result.uuid for result in NameQuery]

        if len(query_uuids) > 0:
          uuids += query_uuids
        else:
          session['result'].append({
            "masked_ic": query[0],
            "full_name": query[1],
            "validity": "Invalid",
            "expiry_date": "Invalid",
            "duration": "Invalid" 
          })

      InternetQuery = (
        db.session.query(MaskedIC, AMPT, VocDate)
        .outerjoin(AMPT)
        .outerjoin(VocDate)
        .filter(MaskedIC.uuid.in_(uuids))
        .all()
      )

      IntranetQuery = (
        db.session.query(FullName)
        .filter(FullName.uuid.in_(uuids))
        .all()
      )

      for row in range(len(uuids)):

        result = {
          "masked_ic": "Invalid",
          "full_name": "Invalid",
          "validity": "Invalid",
          "expiry_date": "Invalid",
          "duration": "Invalid" 
        }

        try:
          for table in InternetQuery[row]:
            table_dict = table.__dict__
            del table_dict['uuid']
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              if column in ["course_date", "ampt_date"]:
                dateDict[column] = value
                result[column] = value.strftime("%Y-%b-%d")
              else:
                result[column]=value
        except:
          pass

        try:
          table_dict = IntranetQuery[row].__dict__
          result["full_name"]=table_dict["full_name"]          
        except:
          pass

        #print(IntranetQuery[row].__dict__)

        try:
          result["validity"], result["expiry_date"], result["duration"] = expiryCalculator(
            date1=dateDict["course_date"],
            date2=dateDict["ampt_date"]
          )
          result["expiry_date"]=result["expiry_date"].strftime("%Y-%b-%d")
        except:
          pass

        session["result"].append(result)
      
      print(session["result"])

    except EmptyQuery:
      formsearch.submitunit.errors.append("No search query detected in input field. Click 'Upload' to populate input field with file.")
      print("error")
    except:
      formsearch.submitunit.errors.append("The query is formatted incorrectly")
  
  if formsearch.downloadunit.data and formsearch.validate():
    return sendExcel(
      dict_in=session['result'], 
      column_order=["masked_ic", "full_name", "validity", "expiry_date", "duration"], 
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

  for key in ['result', 'result_p','tab','profile_modify_check','profile_modify_header']:
    if key not in session:
      session[key] = None

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

      uuids = []

      for query in queries[1:]:
        query_uuids = []

        ICQuery = (
          MaskedIC.query.
          filter(MaskedIC.masked_ic==query[0]).
          all()
        )

        for uuid in [result.uuid for result in ICQuery]:
          NameQuery = (
            FullName.query
            .filter(FullName.uuid==uuid)
            .filter(FullName.full_name==query[1])        
            .all()
          )
          query_uuids = [result.uuid for result in NameQuery]

        if len(query_uuids) > 0:
          uuids += query_uuids
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

      InternetQuery = (
        db.session.query(MaskedIC, AMPT, VocDate)
        .outerjoin(AMPT)
        .outerjoin(VocDate)
        .filter(MaskedIC.uuid.in_(uuids))
        .all()
      )

      IntranetQuery = (
        db.session.query(FullName, VocName, AED)
        .outerjoin(VocName)
        .outerjoin(AED)
        .filter(FullName.uuid.in_(uuids))
        .all()
      )

      for row in range(len(uuids)):

        dateDict = {}

        result = {
          "masked_ic": "Invalid",
          "full_name": "Invalid",
          "validity":   "Invalid",
          "expiry_date": "Invalid",
          "duration": "Invalid",
          "course_name": "Invalid",
          "course_date": "Invalid",
          "ampt_date": "Invalid",
          "aed_name": "Invalid",
          "aed_date": "Invalid",
          "aed_cert": "Invalid"
        }

        try:
          for table in InternetQuery[row]:
            table_dict = table.__dict__
            del table_dict['uuid']
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              if column in ["course_date", "ampt_date"]:
                dateDict[column] = value
                result[column] = value.strftime("%Y-%b-%d")
              else:
                result[column]=value
        except:
          pass

        try:
          for table in IntranetQuery[row]:
            table_dict = table.__dict__
            del table_dict['uuid']
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              if column in ["aed_date"]:
                result[column] = value.strftime("%Y-%b-%d")
              else:
                result[column]=value
        except:
          pass

        print(dateDict)

        try:
          result["validity"], result["expiry_date"], result["duration"] = expiryCalculator(
            date1=dateDict["course_date"],
            date2=dateDict["ampt_date"]
          )
          result["expiry_date"]=result["expiry_date"].strftime("%Y-%b-%d")
        except:
          pass

        session["result"].append(result)

    except EmptyQuery:
      formsearch.submit_smti.errors.append("No search query detected in input field. Click 'Upload' to populate input field with file.")
    except Exception as e:
      print(e)
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

      uuids = []

      for query in queries[1:]:
        query_uuids = []

        ICQuery = (
          MaskedIC.query.
          filter(MaskedIC.masked_ic==query[0]).
          all()
        )

        for uuid in [result.uuid for result in ICQuery]:
          NameQuery = (
            FullName.query
            .filter(FullName.uuid==uuid)
            .filter(FullName.full_name==query[1])        
            .all()
          )
          query_uuids = [result.uuid for result in NameQuery]

        if len(query_uuids) > 0:
          uuids += query_uuids
        else:
          session['result_p'].append({
            "masked_ic": query[0],
            "full_name": query[1],
            "rights": "Invalid" 
          })

      InternetQuery = (
        db.session.query(MaskedIC)
        .filter(MaskedIC.uuid.in_(uuids))
        .all()
      )

      IntranetQuery = (
        db.session.query(FullName, Profile)
        .outerjoin(Profile)
        .filter(FullName.uuid.in_(uuids))
        .all()
      )

      for row in range(len(uuids)):

        result = {
          "masked_ic": query[0],
          "full_name": query[1],
          "rights": "Invalid" 
        }

        try:
          for table in InternetQuery[row]:
            table_dict = table.__dict__
            del table_dict['uuid']
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              result[column]=value
        except:
          pass

        try:
          for table in IntranetQuery[row]:
            table_dict = table.__dict__
            del table_dict['uuid']
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              result[column]=value
        except:
          pass

        session["result_p"].append(result)

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
    class EmptyQuery(Exception):
      """Exception raised when query is empty"""
      pass

    class QueryError(Exception):
      """Exception raised when there is an query error"""
      pass

    try:
      queries = list(csv.reader(q, quotechar='"', quoting=csv.QUOTE_ALL))
      profile_result = []
      del_check=[]
      session["profile_modify_check"] = None
      session["profile_modify_header"] = None

      print(queries)

      if len(queries) == 1:
        raise EmptyQuery()

      if not "uuid" in queries[0]:
        formsearchp.modify_profile.errors.append("Column 'uuid' must be included")
        raise QueryError()

      profile_modify_header = queries[0]

      for query in queries[1:]:

        queryDict = dict(zip(queries[0], query))

        for column, value in queryDict.items():
          if value == "":
            del queryDict[column]
        
        NameQuery = FullName.query.filter(FullName.uuid==queryDict["uuid"]).first()
        ICQuery = MaskedIC.query.filter(MaskedIC.uuid==queryDict["uuid"]).first()
        print("masked_ic" in queryDict)
        print("full_name" in queryDict)

        if(
            NameQuery == None or
            ICQuery == None
          ) and not (
            "masked_ic" in queryDict and 
            "full_name" in queryDict
          ):

          formsearchp.modify_profile.errors.append(queryDict["uuid"] + " does not exist. Create entry by defining 'masked_ic and 'full_name'")
        
        else:
          for column, value in list(queryDict.items()):
            if column == "uuid":
              pass
            elif column == "masked_ic":
              if value == "#DEL":
                formsearchp.modify_profile.errors.append(queryDict["uuid"] + " " + column +" cannot be deleted directly")
              elif re.search("^\d\d\d[A-Za-z]$", value):
                queryDict[column] = value.upper()
              else:
                formsearchp.modify_profile.errors.append(queryDict["uuid"] + " " + column +" is not format of masked IC")
            elif column == "full_name":
              if value == "#DEL":
                formsearchp.modify_profile.errors.append(queryDict["uuid"] + " " + column +" cannot be deleted directly")
            elif column == "rights":
              if value == "#DEL":
                del_check.append(queryDict["uuid"])
              elif value.title() == "Unit":
                queryDict[column] = "Unit"
              elif value.upper() == "SMTI":
                queryDict[column] = "SMTI"
              else:
                formsearchp.modify_profile.errors.append(queryDict["uuid"] + " " + column +" only accepts 'SMTI' or 'Unit' as input")
            else:
              del queryDict[column]
              if column in profile_modify_header:
                profile_modify_header.remove(column)

          profile_result.append(queryDict)

      print(profile_result)
      print(formsearchp.modify_profile.errors)
      print("complete")
      print(session["profile_modify_check"])


      if len(formsearchp.modify_profile.errors)==0:
        session["profile_modify_check"] = profile_result
        session["profile_modify_header"] = profile_modify_header
      else:
        raise QueryError()

    except EmptyQuery:
      formsearchp.modify_profile.errors.append("No modify query detected in input field. Click 'Upload' to populate input field with file.")

    except QueryError:
      print(formsearchp.modify_profile.errors)
      print(session["profile_modify_check"])

    except Exception as e:
      print(e)
      formsearchp.modify_profile.errors.append("The query is formatted incorrectly")
         
  return render_template('smti.html', inet = True, formxls = formxls, formsearch=formsearch, formxlsp = formxlsp, formsearchp=formsearchp)


@app.route('/invalid')
def invalid():
  return render_template('invalid.html', nodate = True)

@app.route('/terms')
def terms():
  return render_template('terms.html', nodate = True)

@app.route('/singpass')
def singpass():
  return render_template('singpass.html', nodate = True)

@app.errorhandler(404)
def page_not_found(self):
  return render_template('404.html', nodate = True)


if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=random.randint(2000, 9000))