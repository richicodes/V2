from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired

from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, UUID

class uuidForm(FlaskForm):
  uuid  = StringField('SingPass UUID', validators=
    [InputRequired(message="No input to process"), UUID(message="Please input valid UUID")])
  submit = SubmitField('Singpass Login')

class csvForm(FlaskForm):
  file = FileField(validators=[FileRequired("Please choose a file to upload"), FileAllowed(["csv"], "Only .csv files are accepted")])
  submit = SubmitField('Upload')

class unitForm(FlaskForm):
  entry = TextAreaField(validators=[InputRequired(message="No input to process")])
  submit = SubmitField('Search')