from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired

from wtforms import StringField, SubmitField, TextAreaField, PasswordField
from wtforms.validators import InputRequired, Regexp

class singpassForm(FlaskForm):
  submit = SubmitField('Log In with SingPass')

class loginForm(FlaskForm):
  username  = StringField('SingPass ID', validators=
    [InputRequired(message="Please Enter SingPass ID"), Regexp('[a-zA-Z][0-9][0-9][0-9][0-9][0-9][0-9][0-9][a-zA-Z]', message="SingPass ID is in IC format")])
  password = PasswordField('Password', validators=
    [InputRequired()])
  submit = SubmitField('Log In')

class logoutForm(FlaskForm):
  submit = SubmitField('Log Out')

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