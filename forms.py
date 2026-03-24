from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SelectField, TextAreaField, IntegerField, DateField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Regexp, NumberRange, Optional, URL

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(message='Имя пользователя обязательно'),
        Length(min=3, max=80, message='Имя пользователя должно быть от 3 до 80 символов'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Имя пользователя может содержать только буквы, цифры и _')
    ])
    accept_terms = BooleanField(
        'Согласие с условиями',
        validators=[DataRequired(message='Для регистрации необходимо принять условия и политику конфиденциальности')]
    )
    email = EmailField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Некорректный email адрес'),
        Length(max=120, message='Email слишком длинный')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=8, message='Пароль должен быть не менее 8 символов'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', 
               message='Пароль должен содержать заглавные и строчные буквы, а также цифры')
    ])
    role = SelectField('Роль', choices=[
        ('student', 'Студент'),
        ('teacher', 'Учитель'),
        ('employer', 'Работодатель')
    ], validators=[
        DataRequired(message='Роль обязательна'),
        Regexp(r'^(student|teacher|employer)$', message='Некорректная роль')
    ])

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(message='Имя пользователя обязательно')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен')
    ])

class StudentProfileForm(FlaskForm):
    first_name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(max=50, message='Имя слишком длинное')
    ])
    last_name = StringField('Фамилия', validators=[
        DataRequired(message='Фамилия обязательна'),
        Length(max=50, message='Фамилия слишком длинная')
    ])
    phone = StringField('Телефон', validators=[
        Optional(),
        Regexp(r'^\+?[1-9]\d{1,14}$', message='Некорректный номер телефона')
    ])
    address = TextAreaField('Адрес', validators=[
        Optional(),
        Length(max=500, message='Адрес слишком длинный')
    ])
    study_form = SelectField('Форма обучения', choices=[
        ('', 'Выберите форму'),
        ('очная', 'Очная'),
        ('заочная', 'Заочная'),
        ('дистанционная', 'Дистанционная')
    ], validators=[Optional()])
    about_me = TextAreaField('О себе', validators=[
        Optional(),
        Length(max=2000, message='Текст слишком длинный')
    ])
    group_id = IntegerField('Группа', validators=[Optional(), NumberRange(min=1)])
    desired_direction_id = IntegerField('Направление', validators=[Optional(), NumberRange(min=1)])
    desired_specialization_id = IntegerField('Специализация', validators=[Optional(), NumberRange(min=1)])
    birth_date = DateField('Дата рождения', validators=[Optional()])

class EmployerProfileForm(FlaskForm):
    company_name = StringField('Название компании', validators=[
        DataRequired(message='Название компании обязательно'),
        Length(max=200, message='Название слишком длинное')
    ])
    company_description = TextAreaField('Описание компании', validators=[
        Optional(),
        Length(max=5000, message='Описание слишком длинное')
    ])
    contact_person = StringField('Контактное лицо', validators=[
        DataRequired(message='Контактное лицо обязательно'),
        Length(max=100, message='Имя слишком длинное')
    ])
    phone = StringField('Телефон', validators=[
        Optional(),
        Regexp(r'^\+?[1-9]\d{1,14}$', message='Некорректный номер телефона')
    ])
    email = EmailField('Email', validators=[
        Optional(),
        Email(message='Некорректный email адрес')
    ])
    website = StringField('Веб-сайт', validators=[
        Optional(),
        URL(message='Некорректный URL')
    ])
    address = TextAreaField('Адрес', validators=[
        Optional(),
        Length(max=500, message='Адрес слишком длинный')
    ])
    industry = StringField('Отрасль', validators=[
        Optional(),
        Length(max=100, message='Отрасль слишком длинная')
    ])
    company_size = SelectField('Размер компании', choices=[
        ('', 'Выберите размер'),
        ('малый', 'Малый'),
        ('средний', 'Средний'),
        ('крупный', 'Крупный')
    ], validators=[Optional()])

