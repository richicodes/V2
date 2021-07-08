from datetime import date
from dateutil.relativedelta import relativedelta

from pandas import DataFrame, ExcelWriter

from flask import send_file

import io

def expiryCalculator(date1, date2):
  if date1==None and date2==None:
    return None, None, None
  else:
    expDate = max(date1, date2) + relativedelta(years=1)
    duration = (expDate-date.today()).days
    if duration > 0:
      eligibility="Valid"
    else:
      eligibility="Invalid"
    return eligibility, expDate, duration

def sendExcel(dict_in, column_order, filename_suffix):
  print("pass")
  print(dict_in)
  output = io.BytesIO()
  df=DataFrame.from_dict(dict_in)[column_order]
  print(df)
  with ExcelWriter(output) as writer:      
    df.to_excel(writer)    
  output.seek(0)

  filename= filename_suffix +"_"+ date.today().strftime("%Y-%m-%d") + ".xlsx"

  return send_file(output, 
    as_attachment=True,
    download_name=filename,
    mimetype="application/vnd.ms-excel"
    )

def multi_getattr(obj, attr, default = "Invalid"):
  """
  Get a named attribute from an object; multi_getattr(x, 'a.b.c.d') is
  equivalent to x.a.b.c.d. When a default argument is given, it is
  returned when any attribute in the chain doesn't exist; without
  it, an exception is raised when a missing attribute is encountered.

  from https://code.activestate.com/recipes/577346-getattr-with-arbitrary-depth/     

  """
  attributes = attr.split(".")
  for i in attributes:
    try:
      obj = getattr(obj, i)
    except:
      return default
  return obj