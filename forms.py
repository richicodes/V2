from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired

from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, UUID

class uuidForm(FlaskForm):
  uuid  = StringField('SingPass UUID', validators=
    [InputRequired(message="No input to process"), UUID(message="Please input valid UUID")])
  submit = SubmitField('Singpass Login')

class xlsForm(FlaskForm):
  file = FileField(validators=[FileRequired(), FileAllowed(["xlsx"], "Only .xlsx files are accepted")])
  submitxls = SubmitField('Upload')

class unitForm(FlaskForm):
  entry = TextAreaField(validators=[InputRequired(message="No input to process")])
  submitunit = SubmitField('Search')
  downloadunit = SubmitField('Download')