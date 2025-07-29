from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DateField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email

class RegisterForm(FlaskForm):
    list_id = HiddenField()
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class LoginForm(FlaskForm):
    list_id = HiddenField()
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class EmailForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Next')

class ResetPasswordForm(FlaskForm):
    code = StringField('Enter Verification Code', validators=[DataRequired()])
    pass1 = PasswordField('Enter New Password', validators=[DataRequired()])
    pass2 = PasswordField('Re-enter Password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')

class AddListForm(FlaskForm):
    title = StringField('List Title', validators=[DataRequired()])
    submit = SubmitField('Create List')

class DateForm(FlaskForm):
    date = DateField(validators=[DataRequired()])
    submit = SubmitField('✔')

class DeleteForm(FlaskForm):
    sure = SelectField('Are you sure?', choices=['Yes', 'No'], validators=[DataRequired()])
    submit = SubmitField('Submit')