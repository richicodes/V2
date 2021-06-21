from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField, FileField, TextAreaField
from wtforms.validators import InputRequired, UUID, regexp

class uuidForm(FlaskForm):
  uuid  = StringField('SingPass UUID', validators=
    [InputRequired(message="No input to process"), UUID(message="Please input valid UUID")])
  submit = SubmitField('Singpass Login')

''' class unitForm(FlaskForm):
  file = FileField('Choose File', validators=
    [regexp(u'^[^/\\]\.csv$', message = "Please choose a .csv file")])
  entry = TextAreaField(validators=[InputRequired(message="No input to process")])
  search = SubmitField('Search') '''