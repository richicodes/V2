from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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

class IC(db.Model):
  __bind_key__= "fakepass"
  __tablename__ = "ic"
  uuid = db.Column(db.String(), db.ForeignKey('full_name.uuid'), primary_key=True, unique=True, nullable=False)
  ic = db.Column(db.String(), nullable=False, unique=True)