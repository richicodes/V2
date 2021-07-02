from datetime import date
from dateutil.relativedelta import relativedelta

def expiryCalculator(date1, date2):
  if date1==None and date2==None:
    return None, None, None
  else:
    expDate = max(date1, date2) + relativedelta(years=1)
    duration = (expDate-date.today()).days
    eligibility = duration > 0
    return eligibility, expDate, duration

    

