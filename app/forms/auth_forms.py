"""Authentication forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from flask_login import current_user
from app.models.user import User


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign In")


class SignupForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(2, 80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(2, 80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone")
    password = PasswordField("Password", validators=[DataRequired(), Length(6, 128)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email already registered.")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class PasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(6, 128)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Reset Password")


class ProfileForm(FlaskForm):
    first_name = StringField("First Name", validators=[Length(2, 80)])
    last_name = StringField("Last Name", validators=[Length(2, 80)])
    email = StringField("Email", validators=[Email()])
    phone = StringField("WhatsApp Number", validators=[DataRequired()])
    submit = SubmitField("Save Changes")

    def validate_email(self, field):
        if field.data:
            existing = User.query.filter(
                User.email == field.data.lower().strip(),
                User.id != current_user.id,
            ).first()
            if existing:
                raise ValidationError("Email already in use.")
