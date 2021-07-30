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
      results = []
      session["result"] = []
      uuids_results = []

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
          uuids_results += query_uuids
        else:
          uuids_results.append({
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

        dateDict = {}

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
          result["uuid"]=table_dict["uuid"]        
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

        results.append(result)
      
      for uuid in uuids_results:
        print(uuid)
        print(type(uuid))
        if isinstance(uuid, dict):
          session["result"].append(uuid)
        else:
          for result in results:
            if result['uuid']==uuid:
              session["result"].append(result)
      
      print(session["result"])

    except EmptyQuery:
      formsearch.submitunit.errors.append("No search query detected in input field. Click 'Upload' to populate input field with file.")
      print("error")
    except Exception as e:
      print("ERROR")
      print(e)      
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
  formmodify = smtiModifyForm()

  formxlsp = profileXlsxForm()
  formsearchp = profileSearchForm(
    entry_profile='"Masked NRIC (123X)","FULL NAME"'
  )
  formmodifyp = profileModifyForm()

  for key in ['result', 'smti_modify_check','profile_modify_header', 'result_modify_p','result_p','profile_modify_check','profile_modify_header', 'result_modify_p']:
    if key not in session:
      session[key] = None

  if 'tab' not in session:
    session['tab'] = 'smti'

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
      uuids_results = []
      results = []

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
          uuids_results += query_uuids
        else:
          uuids_results.append({
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
        .order_by(MaskedIC.uuid)
        .all()
      )

      IntranetQuery = (
        db.session.query(FullName, VocName, AED)
        .outerjoin(VocName)
        .outerjoin(AED)
        .filter(FullName.uuid.in_(uuids))
        .order_by(FullName.uuid)
        .all()
      )

      for row in range(len(InternetQuery)):

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
            try:
              table_dict = table.__dict__
              print(table_dict['uuid'])
              del table_dict['_sa_instance_state']
              for column, value in table_dict.items():
                if column in ["course_date", "ampt_date"]:
                  dateDict[column] = value
                  result[column] = value.strftime("%Y-%b-%d")
                else:
                  result[column]=value
            except:
              pass
        except:
          pass

        try:
          for table in IntranetQuery[row]:
            try:
              table_dict = table.__dict__
              print(table_dict['uuid'])
              del table_dict['uuid']
              del table_dict['_sa_instance_state']
              for column, value in table_dict.items():
                if column in ["aed_date"]:
                  result[column] = value.strftime("%Y-%b-%d")
                else:
                  result[column]=value
            except:
              pass
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

        results.append(result)

      for uuid in uuids_results:
        print(uuid)
        print(type(uuid))
        if isinstance(uuid, dict):
          session["result"].append(uuid)
        else:
          for result in results:
            if result['uuid']==uuid:
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
      column_order=["masked_ic", "full_name", "validity", "expiry_date", "duration", "course_name", "course_date", "ampt_date", "aed_name", "aed_date", "aed_cert"], 
      filename_suffix="eMedic"
      )

  if formsearch.modify_smti.data and formsearch.validate():
    session['tab'] = "smti"
    q = formsearch.entry_smti.data.splitlines()
    class EmptyQuery(Exception):
      """Exception raised when query is empty"""
      pass

    class QueryError(Exception):
      """Exception raised when there is an query error"""
      pass

    try:
      queries = list(csv.reader(q, quotechar='"', quoting=csv.QUOTE_ALL))

      print(queries)

      if len(queries) == 1:
        raise EmptyQuery()

      if not "uuid" in queries[0]:
        formsearch.modify_smti.errors.append("Column 'uuid' must be included")
        raise QueryError()

      smti_result = []
      query_dicts = []
      session["smti_modify_check"] = None
      session["smti_modify_header"] = None

      for query in queries[1:]:

        query_dict = dict(zip(queries[0], query))

        for column, value in list(query_dict.items()):
          if column not in ["uuid", "masked_ic", "full_name", "course_name", "course_date", "ampt_date", "aed_name", "aed_date", "aed_cert"]:
            del query_dict[column]
          elif value == "":
            del query_dict[column]
        
        query_dicts.append(query_dict)

      for column in queries[0]:
        if column not in ["uuid", "masked_ic", "full_name", "course_name", "course_date", "ampt_date", "aed_name", "aed_date", "aed_cert"]:
          queries[0].remove(column)

      for query_dict in query_dicts:
        
        NameQuery = FullName.query.filter(FullName.uuid==query_dict["uuid"]).first()
        ICQuery = MaskedIC.query.filter(MaskedIC.uuid==query_dict["uuid"]).first()

        if(
            NameQuery == None or
            ICQuery == None
          ) and not (
            "masked_ic" in query_dict and 
            "full_name" in query_dict
          ):

          formsearch.modify_smti.errors.append(query_dict["uuid"] + " does not exist. Create entry by defining 'masked_ic and 'full_name'")
        
        else:
          delete_check = []
          course_field = 0
          course_del = 0
          aed_field = 0
          aed_del = 0

          for column, value in list(query_dict.items()):
            if column == "uuid":
              pass
            elif column == "masked_ic":
              if value == "#DEL":
                formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" cannot be deleted directly")
              elif re.search("^\d\d\d[A-Za-z]$", value):
                query_dict[column] = value.upper()
              else:
                formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" is not format of masked IC")
            elif column == "full_name":
              if value == "#DEL":
                formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" cannot be deleted directly")
            elif column == "course_name":
              if value == "#DEL":
                course_dict[column] = value.upper()
                course_field += 1
                course_del += 1
              elif value.upper() in ['EMT', 'EMTS', 'MVT', 'BCS']:
                query_dict[column] = value.upper()
                course_field += 1
              else:
                formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" only accepts 'EMT', 'EMTS', 'MVT' or 'BCS' as input")
            elif column == "course_date":
              if value == "#DEL":
                query_dict[column] = value
                course_field += 1
                course_del += 1
              else:
                try:
                  course_field += 1
                  datetime.strptime(value, "%Y-%b-%d")
                except Exception as e:
                  print(e)
                  formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" only accepts '#DEL' or date in YYYY-MMM-DD  as input")
            elif column == "ampt_date":
              if value == "#DEL":
                query_dict[column] = value
              else:
                try:
                  delete_check.append(column)
                  datetime.strptime(value, "%Y-%b-%d")
                  print(type(query_dict[column]))
                except Exception as e:
                  print(e)
                  formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" only accepts '#DEL' or date in YYYY-MMM-DD  as input")
            elif column == "aed_name":
              if value == "#DEL":
                query_dict[column] = value
                aed_field += 1
                aed_del += 1
              elif value.upper() in ['CPR+AED', 'BCLS+AED']:
                query_dict[column] = value.upper()
                aed_field += 1
              else:
                formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" only accepts 'CPR+AED' or 'BCLS+AED' as input")
            elif column == "aed_date":
              if value == "#DEL":
                query_dict[column] = value
                aed_field += 1
                aed_del += 1
              else:
                try:
                  aed_field += 1
                  datetime.strptime(value, "%Y-%b-%d")
                except Exception as e:
                  print(e)
                  formsearch.modify_smti.errors.append(query_dict["uuid"] + " " + column +" only accepts '#DEL' or date in YYYY-MMM-DD as input")
            elif column == "aed_cert":
              if value == "#DEL":
                query_dict[column] = value
                aed_field += 1
                aed_del += 1
              else:
                query_dict[column] = value
                aed_field += 1
            else:
              del query_dict[column]
              if column in session['smti_modify_header']:
                session['smti_modify_header'].remove(column)

            if course_field > 0:
              if course_del == 1:
                formsearch.modify_smti.errors.append(query_dict["uuid"] + " must have '#DEL' in 'course_name' and 'course_date'")
              if course_del == 2:
                delete_check.append('course')
              elif course_field == 1:
                InternetQuery = (
                  db.session.query(VocDate)
                  .filter(VocDate.uuid == query_dict["uuid"])
                  .one()
                )
                IntranetQuery = (
                  db.session.query(VocName)
                  .filter(VocName.uuid == query_dict["uuid"])
                  .one()
                )
                if InternetQuery == None and IntranetQuery == None:
                  formsearch.modify_smti.errors.append(query_dict["uuid"] + " 'course_name' and 'course_date' must be defined together to create a new entry")

            if aed_field > 0:
              if 0 < aed_del < 3:
                formsearch.modify_smti.errors.append(query_dict["uuid"] + " must have '#DEL' in 'aed_name', 'aed_date' and 'aed_cert'")
              if aed_del == 3:
                delete_check.append('aed')
              elif aed_field < 3:
                IntranetQuery = (
                  db.session.query(VocName)
                  .filter(AED.uuid == query_dict["uuid"])
                  .one()
                )
                if IntranetQuery == None:
                  formsearch.modify_smti.errors.append(query_dict["uuid"] + " 'course_name' and 'course_date' must be defined together to create a new entry")

          if len(delete_check) > 0:

            InternetQuery = (
              db.session.query(MaskedIC, AMPT, VocDate)
              .outerjoin(AMPT)
              .outerjoin(VocDate)
              .filter(MaskedIC.uuid == query_dict["uuid"])
              .one()
            )

            IntranetQuery = (
              db.session.query(FullName, VocName, AED, Profile)
              .outerjoin(VocName)
              .outerjoin(AED)
              .outerjoin(Profile)
              .filter(FullName.uuid == query_dict["uuid"])
              .one()
            )

            if (
              (InternetQuery.AMPT == None or 'ampt_date' in delete_check) and
              ((InternetQuery.VocDate == None and IntranetQuery.VocName == None) or 'course' in delete_check) and
              (IntranetQuery.AED == None or 'aed' in delete_check) and
              IntranetQuery.Profile == None
            ):
              for column in ['full_name', 'masked_ic']:
                if column not in queries[0]:
                  queries[0].append(column)
                  print(queries[0])
              for column in queries[0]:
                if column == 'uuid':
                  query_dict[column] = '#DEL ' + query_dict[column]
                else:
                  query_dict[column] = '#DEL'
            else:
              print("DONTDELETE")

          smti_result.append(query_dict)

      print(smti_result)
      print(formsearch.modify_smti.errors)
      print("complete")
      print(queries[0])

      if len(formsearch.modify_smti.errors)==0:
        session["smti_modify_check"] = smti_result
        session["smti_modify_header"] = queries[0]
        print('updated')
      else:
        raise QueryError()

    except EmptyQuery:
      formsearch.modify_smti.errors.append("No modify query detected in input field. Click 'Upload' to populate input field with file.")

    except QueryError:
      print(formsearch.modify_smti.errors)
      print(session["profile_modify_check"])

    except Exception as e:
      print(e)
      formsearch.modify_smti.errors.append("The query is formatted incorrectly")

  if formmodify.download_modify_smti.data and formmodify.validate():
    session['tab'] = "smtiSearchForm"
    return sendExcel(
      dict_in=session["smti_modify_check"], 
      column_order=session["smti_modify_header"],
      filename_suffix="modify_smti"
      )




  if formmodify.submit_modify_smti.data and formmodify.validate():

    uuids = []
    results = []
    session["result_modify"] = []
    print(session["smti_modify_check"])

    for row in session["smti_modify_check"]:

      uuids.append(row['uuid'][-36:])

      if row['uuid'][0:4] == '#DEL':

        print(row['uuid'] + " is being deleted")

        entry = (
          db.session.query(AMPT)
          .filter(AMPT.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL AMPT')
        entry = (
          db.session.query(VocDate)
          .filter(VocDate.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL VocDate')
        entry = (
          db.session.query(VocName)
          .filter(VocName.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL VocName')
        entry = (
          db.session.query(AED)
          .filter(AED.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL AED')

        entry = (
          db.session.query(FullName)
          .filter(FullName.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL full_name')
        entry = (
          db.session.query(MaskedIC)
          .filter(MaskedIC.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL masked_ic')
      
      else:
        for column in session["smti_modify_header"]:
          
          cell = None
          try:
            cell = row[column]
          except:
            pass

          print(cell)
          print(column)

          if cell == None or column == 'uuid':
            print("pass")
          elif cell == '#DEL':
            if column == 'ampt_date':
              entry = (
                db.session.query(AMPT)
                .filter(AMPT.uuid == row['uuid'][-36:])
              )
              entry.delete()
              print('#DEL AMPT')
            elif column == 'course_date':
              entry = (
                db.session.query(VocDate)
                .filter(VocDate.uuid == row['uuid'][-36:])
              )
              entry.delete()
              print('#DEL VocDate')
            elif column == 'course_name':
              entry = (
                db.session.query(VocName)
                .filter(VocName.uuid == row['uuid'][-36:])
              )
              entry.delete()
              print('#DEL VocName')
            elif column == 'aed_cert':
              entry = (
                db.session.query(AED)
                .filter(AED.uuid == row['uuid'][-36:])
              )
              entry.delete()
              print('#DEL AED')
          else:
            if column == 'full_name':
              entry = FullName(uuid=row['uuid'], full_name=cell)
              db.session.merge(entry)
              print("full_name changed")
            elif column == 'masked_ic':
              entry = MaskedIC(uuid=row['uuid'], masked_ic=cell)
              db.session.merge(entry)
              print("masked_ic changed")
            elif column == 'ampt_date':
              cell_date =  datetime.strptime(cell, "%Y-%b-%d").date()
              print(type(cell_date))
              entry = AMPT(uuid=row['uuid'], ampt_date=cell_date)
              db.session.merge(entry)
              print('ampt_date changed')
            elif column == 'course_date':
              cell_date =  datetime.strptime(cell, "%Y-%b-%d").date()
              entry = VocDate(uuid=row['uuid'], course_date=cell_date)
              db.session.merge(entry)
              print('course_date changed')
            elif column == 'course_name':
              entry = VocName(uuid=row['uuid'], course_name=cell)
              db.session.merge(entry)
              print('course_name changed')
            elif column == 'aed_name':
              entry = AED(uuid=row['uuid'], aed_name=cell)
              db.session.merge(entry)
              print('aed_name changed')
            elif column == 'aed_date':
              cell_date =  datetime.strptime(cell, "%Y-%b-%d").date()
              entry = AED(uuid=row['uuid'], aed_date=cell_date)
              db.session.merge(entry)
              print('aed_date changed')
            elif column == 'aed_cert':
              entry = AED(uuid=row['uuid'], aed_cert=cell)
              db.session.merge(entry)
              print('aed_cert changed')

    db.session.commit()

    InternetQueryResult = (
      db.session.query(MaskedIC, AMPT, VocDate)
      .outerjoin(AMPT)
      .outerjoin(VocDate)
      .filter(MaskedIC.uuid.in_(uuids))
      .order_by(MaskedIC.uuid)
      .all()
    )

    IntranetQueryResult = (
      db.session.query(FullName, VocName, AED)
      .outerjoin(VocName)
      .outerjoin(AED)
      .filter(FullName.uuid.in_(uuids))
      .order_by(FullName.uuid)
      .all()
    )

    print(uuids)

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
        for table in InternetQueryResult[row]:
          try:
            table_dict = table.__dict__
            print(table_dict['uuid'])
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              if column in ["course_date", "ampt_date"]:
                dateDict[column] = value
                result[column] = value.strftime("%Y-%b-%d")
              else:
                result[column]=value
          except:
            pass
      except:
        pass

      try:
        for table in IntranetQueryResult[row]:
          try:
            table_dict = table.__dict__
            print(table_dict['uuid'])
            del table_dict['uuid']
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              if column in ["aed_date"]:
                result[column] = value.strftime("%Y-%b-%d")
              else:
                result[column]=value
          except:
            pass
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

      results.append(result)

    print(results)

    for uuid in uuids:
      empty = True
      for result in results:
        try:
          if result['uuid']==uuid:
            session["result_modify"].append(result)
            empty = False
        except:
          pass
      
      if empty:
        session["result_modify"].append({
        "uuid": uuid,
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
      })
    
    print(session["result_modify"])

  if formmodify.download_result_smti.data and formmodify.validate():
    session['tab'] = "smti"
    return sendExcel(
      dict_in=session["result_modify"], 
      column_order=['uuid', 'masked_ic', 'full_name', "validity", "expiry_date", "duration", "course_name", "course_date", "ampt_date", "aed_name", "aed_date", "aed_cert"],
      filename_suffix="modify_smti_result"
      )

  if formmodify.cancel_modify_smti.data and formmodify.validate():
    session['tab'] = "smti"
    session["smti_modify_check"] = None
    session["smti_modify_header"] = None
    session["result_modify"] = None

  if formmodify.exit_modify_smti.data and formmodify.validate():
    session['tab'] = "smti"
    session["smti_modify_check"] = None
    session["smti_modify_header"] = None
    session["result_modify"] = None

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
      results = []
      session["result_p"] = []
      uuids_results = []

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
          uuids_results += query_uuids
        else:
          uuids_results.append({
            "masked_ic": query[0],
            "full_name": query[1],
            "rights": "Invalid" 
          })

      InternetQuery = (
        db.session.query(MaskedIC)
        .filter(MaskedIC.uuid.in_(uuids))
        .order_by(MaskedIC.uuid)
        .all()
      )

      IntranetQuery = (
        db.session.query(FullName, Profile)
        .outerjoin(Profile)
        .filter(FullName.uuid.in_(uuids))
        .order_by(FullName.uuid)
        .all()
      )

      for row in range(len(InternetQuery)):
        result = {
            "rights": "Invalid" 
        }
        try:
          table_dict = InternetQuery[row].__dict__
          del table_dict['_sa_instance_state']
          for column, value in table_dict.items():
            result[column]=value
        except:
          pass

        try:
          for table in IntranetQuery[row]:
            try:
              table_dict = table.__dict__
              del table_dict['uuid']
              del table_dict['_sa_instance_state']
              for column, value in table_dict.items():
                result[column]=value
            except:
              pass
        except:
          pass

        results.append(result)
      
      for uuid in uuids_results:
        print(uuid)
        print(type(uuid))
        if isinstance(uuid, dict):
          session["result_p"].append(uuid)
        else:
          for result in results:
            if result['uuid']==uuid:
              session["result_p"].append(result)


    except EmptyQuery:
      formsearchp.submit_profile.errors.append("No search query detected in input field. Click 'Upload' to populate input field with file.")
    except Exception as e:
      print("ERROR")
      print(e)
      formsearchp.submit_profile.errors.append("The query is formatted incorrectly")
  
  if formsearchp.download_profile.data and formsearchp.validate():
    session['tab'] = "profile"
    return sendExcel(
      dict_in=session['result_p'], 
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

      print(queries)

      if len(queries) == 1:
        raise EmptyQuery()

      if not "uuid" in queries[0]:
        formsearchp.modify_profile.errors.append("Column 'uuid' must be included")
        raise QueryError()

      profile_result = []
      query_dicts = []
      session["profile_modify_check"] = None
      session["profile_modify_header"] = None

      for query in queries[1:]:

        query_dict = dict(zip(queries[0], query))

        for column, value in list(query_dict.items()):
          if column not in ['uuid', 'full_name', 'masked_ic', 'rights']:
            del query_dict[column]
          elif value == "":
            del query_dict[column]
        
        query_dicts.append(query_dict)

      for column in queries[0]:
        if column not in ['uuid', 'full_name', 'masked_ic', 'rights']:
          queries[0].remove(column)

      for query_dict in query_dicts:
        
        NameQuery = FullName.query.filter(FullName.uuid==query_dict["uuid"]).first()
        ICQuery = MaskedIC.query.filter(MaskedIC.uuid==query_dict["uuid"]).first()

        if(
            NameQuery == None or
            ICQuery == None
          ) and not (
            "masked_ic" in query_dict and 
            "full_name" in query_dict
          ):

          formsearchp.modify_profile.errors.append(query_dict["uuid"] + " does not exist. Create entry by defining 'masked_ic and 'full_name'")
        
        else:
          delete_check = False
          for column, value in list(query_dict.items()):
            if column == "uuid":
              pass
            elif column == "masked_ic":
              if value == "#DEL":
                formsearchp.modify_profile.errors.append(query_dict["uuid"] + " " + column +" cannot be deleted directly")
              elif re.search("^\d\d\d[A-Za-z]$", value):
                query_dict[column] = value.upper()
              else:
                formsearchp.modify_profile.errors.append(query_dict["uuid"] + " " + column +" is not format of masked IC")
            elif column == "full_name":
              if value == "#DEL":
                formsearchp.modify_profile.errors.append(query_dict["uuid"] + " " + column +" cannot be deleted directly")
            elif column == "rights":
              if value == "#DEL":
                delete_check = True
              elif value.title() == "Unit":
                query_dict[column] = "Unit"
              elif value.upper() == "SMTI":
                query_dict[column] = "SMTI"
              else:
                formsearchp.modify_profile.errors.append(query_dict["uuid"] + " " + column +" only accepts 'SMTI' or 'Unit' as input")
            else:
              del query_dict[column]
              if column in session['profile_modify_header']:
                session['profile_modify_header'].remove(column)
            
          if delete_check:

            InternetQuery = (
              db.session.query(MaskedIC, AMPT, VocDate)
              .outerjoin(AMPT)
              .outerjoin(VocDate)
              .filter(MaskedIC.uuid == query_dict["uuid"])
              .one()
            )

            IntranetQuery = (
              db.session.query(FullName, VocName, AED)
              .outerjoin(VocName)
              .outerjoin(AED)
              .filter(FullName.uuid == query_dict["uuid"])
              .one()
            )

            if (
              InternetQuery.AMPT == None and
              InternetQuery.VocDate == None and
              IntranetQuery.VocName == None and
              IntranetQuery.AED == None
            ):
              for column in ['full_name', 'masked_ic']:
                if column not in queries[0]:
                  queries[0].append(column)
                  print(queries[0])
              for column in queries[0]:
                if column == 'uuid':
                  query_dict[column] = '#DEL ' + query_dict[column]
                else:
                  query_dict[column] = '#DEL'
            else:
              print("DONTDELETE")

          profile_result.append(query_dict)

      print(profile_result)
      print(formsearchp.modify_profile.errors)
      print("complete")
      print(queries[0])


      if len(formsearchp.modify_profile.errors)==0:
        session["profile_modify_check"] = profile_result
        session["profile_modify_header"] = queries[0]
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

  if formmodifyp.download_modify_profile.data and formmodifyp.validate():
    session['tab'] = "profile"
    return sendExcel(
      dict_in=session["profile_modify_check"], 
      column_order=session["profile_modify_header"],
      filename_suffix="modify_profiles"
      )

  if formmodifyp.submit_modify_profile.data and formmodifyp.validate():

    uuids = []
    results = []
    session["result_modify_p"] = []

    for row in session["profile_modify_check"]:

      uuids.append(row['uuid'][-36:])

      if row['uuid'][0:4] == '#DEL':

        print(row['uuid'] + " is being deleted")

        entry = (
          db.session.query(Profile)
          .filter(Profile.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL rights')
        entry = (
          db.session.query(FullName)
          .filter(FullName.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL full_name')
        entry = (
          db.session.query(MaskedIC)
          .filter(MaskedIC.uuid == row['uuid'][-36:])
        )
        entry.delete()
        print('#DEL masked_ic')
      
      else:
        for column in session["profile_modify_header"]:
          
          cell = None
          try:
            cell = row[column]
          except:
            pass

          print(cell)
          print(column)

          if cell == None or column == 'uuid':
            print("pass")
          elif cell == '#DEL':
            ''' if column == 'fullname':
              entry = (
                db.session.query(FullName)
                .filter(FullName.uuid == row['uuid'])
              )
              entry.delete()
              print('#DEL full_name')
            elif column == 'masked_ic':
              entry = (
                db.session.query(MaskedIC)
                .filter(MaskedIC.uuid == row['uuid'])
              )
              entry.delete()
              print('#DEL masked_ic') '''
            if column == 'rights':
              entry = (
                db.session.query(Profile)
                .filter(Profile.uuid == row['uuid'])
              )
              entry.delete()
              print('#DEL rights')
          else:
            if column == 'full_name':
              entry = FullName(uuid=row['uuid'], full_name=cell)
              db.session.merge(entry)
              print("full_name changed")
            elif column == 'masked_ic':
              entry = MaskedIC(uuid=row['uuid'], masked_ic=cell)
              db.session.merge(entry)
              print("masked_ic changed")
            elif column == 'rights':
              entry = Profile(uuid=row['uuid'], rights=cell)
              db.session.merge(entry)
              print('rights changed')

    db.session.commit()

    InternetQueryResult = (
      db.session.query(MaskedIC)
      .filter(MaskedIC.uuid.in_(uuids))
      .order_by(MaskedIC.uuid)
      .all()
    )

    IntranetQueryResult = (
      db.session.query(FullName, Profile)
      .outerjoin(Profile)
      .filter(FullName.uuid.in_(uuids))
      .order_by(FullName.uuid)
      .all()
    )

    print(uuids)

    for row in range(len(uuids)):

      result = {
        "masked_ic": "Invalid",
        "full_name": "Invalid",
        "rights": "Invalid" 
      }

      try:
        table_dict = InternetQueryResult[row].__dict__
        print(table_dict['uuid'])
        #del uuids.remove([table_dict['uuid']])
        del table_dict['_sa_instance_state']
        for column, value in table_dict.items():
          result[column]=value
      except:
        pass

      try:
        for table in IntranetQueryResult[row]:
          try:
            table_dict = table.__dict__
            print(table_dict['uuid'])
            del table_dict['uuid']
            del table_dict['_sa_instance_state']
            for column, value in table_dict.items():
              result[column]=value
          except:
            pass
      except:
        pass

      results.append(result)

    for uuid in uuids:
      empty = True
      for result in results:
        try:
          if result['uuid']==uuid:
            session["result_modify_p"].append(result)
            empty = False
        except:
          pass
      
      if empty:
        session["result_modify_p"].append({
        "uuid": uuid,
        "masked_ic": "Invalid",
        "full_name": "Invalid",
        "rights": "Invalid" 
      })

  if formmodifyp.download_result_profile.data and formmodifyp.validate():
    session['tab'] = "profile"
    return sendExcel(
      dict_in=session["result_modify_p"], 
      column_order=['uuid', 'masked_ic', 'full_name', 'rights'],
      filename_suffix="modify_profiles_result"
      )

  if formmodifyp.cancel_modify_profile.data and formmodifyp.validate():
    session["profile_modify_check"] = None
    session["profile_modify_header"] = None
    session["result_modify_p"] = None

  if formmodifyp.exit_modify_profile.data and formmodifyp.validate():
    session["profile_modify_check"] = None
    session["profile_modify_header"] = None
    session["result_modify_p"] = None

  return render_template('smti.html', inet = True, formxls = formxls, formsearch=formsearch, formmodify=formmodify, formxlsp = formxlsp, formsearchp=formsearchp, formmodifyp=formmodifyp)


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