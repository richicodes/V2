from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired

from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, UUID

class uuidForm(FlaskForm):
  uuid  = StringField('SingPass UUID', validators=
    [InputRequired(message="No input to process"), UUID(message="Please input valid UUID")])
  submit = SubmitField('Singpass Login')

class unitXlsxForm(FlaskForm):
  file = FileField(validators=[FileRequired(), FileAllowed(["xlsx"], "Only .xlsx files are accepted")])
  submitxls = SubmitField('Upload')

class unitSearchForm(FlaskForm):
  entry = TextAreaField(validators=[InputRequired(message="No input to process")])
  submitunit = SubmitField('Search')
  downloadunit = SubmitField('Download')

class smtiXlsxForm(FlaskForm):
  file_smti = FileField(validators=[FileRequired(), FileAllowed(["xlsx"], "Only .xlsx files are accepted")])
  submitxls_smti = SubmitField('Upload')

class smtiSearchForm(FlaskForm):
  entry_smti = TextAreaField(validators=[InputRequired(message="No input to process")])
  submit_smti = SubmitField('Search')
  download_smti = SubmitField('Download')
  modify_smti = SubmitField('Modify')

class smtiModifyForm(FlaskForm):
  submit_modify_smti = SubmitField('Confirm Modifications')
  download_modify_smti = SubmitField('Download Modifications')
  download_result_smti = SubmitField('Download Results')
  cancel_modify_smti = SubmitField('Cancel')
  exit_modify_smti = SubmitField('Exit')

class profileXlsxForm(FlaskForm):
  file_profile = FileField(validators=[FileRequired(), FileAllowed(["xlsx"], "Only .xlsx files are accepted")])
  submitxls_profile = SubmitField('Upload')

class profileSearchForm(FlaskForm):
  entry_profile = TextAreaField(validators=[InputRequired(message="No input to process")])
  submit_profile = SubmitField('Search')
  download_profile = SubmitField('Download')
  modify_profile = SubmitField('Modify')

class profileModifyForm(FlaskForm):
  submit_modify_profile = SubmitField('Confirm Modifications')
  download_modify_profile = SubmitField('Download Modifications')
  download_result_profile = SubmitField('Download Results')
  cancel_modify_profile = SubmitField('Cancel')
  exit_modify_profile = SubmitField('Exit')