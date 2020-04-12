from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo


class RegistrationForm(FlaskForm):
    username = StringField(label='username', validators=[DataRequired(), Length(min=3, max=8)])
    email = StringField(label='email', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired(), Length(min=5)])
    confirm_password = PasswordField(label='Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(label='Register')


class LoginForm(FlaskForm):
    email = StringField(label='Email',
                        validators=[DataRequired(), Email(message='Enter valid email')])
    password = PasswordField(label='Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField(label='Log In')


class SearchForm(FlaskForm):
    search_ip = StringField(label='search', validators=[DataRequired()])
    submit = SubmitField(label='search')
