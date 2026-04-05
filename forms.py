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

class RegisterVerifyForm(FlaskForm):
    code = StringField('Код из письма', validators=[
        DataRequired(message='Введите код'),
        Length(min=6, max=6, message='Код должен состоять из 6 цифр'),
        Regexp(r'^\d{6}$', message='Код должен содержать только цифры')
    ])


class PasswordLoginForm(FlaskForm):
    login_identifier = StringField('Логин или email', validators=[
        DataRequired(message='Укажите логин или email')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен')
    ])


class LoginRequestCodeForm(FlaskForm):
    login_identifier = StringField('Логин или email', validators=[
        DataRequired(message='Укажите логин или email')
    ])


class LoginVerifyCodeForm(FlaskForm):
    login_identifier = StringField('Логин или email', validators=[
        DataRequired(message='Укажите логин или email')
    ])
    code = StringField('Код из письма', validators=[
        DataRequired(message='Введите код'),
        Length(min=6, max=6, message='Код должен состоять из 6 цифр'),
        Regexp(r'^\d{6}$', message='Код должен содержать только цифры')
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
        Regexp(
            r'^\+?[0-9\s\-\(\)]{7,20}$',
            message='Некорректный номер телефона'
        )
    ])
    city = StringField('Населённый пункт проживания', validators=[
        Optional(),
        Length(max=200, message='Название города слишком длинное')
    ])
    ready_for_business_trips = BooleanField('Готовность к командировкам', validators=[Optional()])
    study_form = SelectField('Форма обучения', choices=[
        ('', 'Выберите форму'),
        ('очная', 'Очная'),
        ('заочная', 'Заочная'),
        ('дистанционная', 'Дистанционная')
    ], validators=[Optional()])
    about_me = TextAreaField('О себе (владение ПО, хобби, достижения, мотивация)', validators=[
        Optional(),
        Length(max=2000, message='Текст слишком длинный')
    ])
    group_id = IntegerField('Группа', validators=[Optional(), NumberRange(min=1)])
    desired_direction_id = IntegerField('Направление', validators=[Optional(), NumberRange(min=1)])
    desired_specialization_id = IntegerField('Специализация', validators=[Optional(), NumberRange(min=1)])
    birth_date = DateField('Дата рождения', validators=[Optional()])

class EmployerProfileForm(FlaskForm):
    company_name = StringField('Название организации', validators=[
        DataRequired(message='Название организации обязательно'),
        Length(max=200, message='Название слишком длинное')
    ])
    ogrn = StringField(
        'ОГРН / ОГРНИП',
        filters=[lambda x: x.strip() if isinstance(x, str) else x],
        validators=[
            Optional(),
            Length(max=15, message='ОГРН не более 15 цифр'),
            Regexp(r'^\d{13}(\d{2})?$', message='Укажите 13 цифр ОГРН или 15 цифр ОГРНИП'),
        ],
    )
    company_description = TextAreaField('Описание компании', validators=[
        Optional(),
        Length(max=5000, message='Описание слишком длинное')
    ])
    contact_person = StringField('ФИО ответственного', validators=[
        DataRequired(message='ФИО ответственного обязательно'),
        Length(max=100, message='ФИО слишком длинное')
    ])
    responsible_position = StringField(
        'Должность ответственного',
        filters=[lambda x: x.strip() if isinstance(x, str) else x],
        validators=[Optional(), Length(max=150, message='Должность слишком длинная')],
    )
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

