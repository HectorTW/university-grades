from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from forms import RegistrationForm, LoginForm, StudentProfileForm, EmployerProfileForm
from schemas import SubmitGradesSchema, InvitationSchema
from tokens import TOKEN_CATALOG, TOKEN_TYPES
from marshmallow import ValidationError

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)

# Окружение приложения (используем отдельную переменную, т.к. FLASK_ENV устарел)
APP_ENV = os.getenv('APP_ENV', os.getenv('FLASK_ENV', 'development')).lower()
IS_PRODUCTION = APP_ENV == 'production'
app.config['APP_ENV'] = APP_ENV

# Конфигурация из переменных окружения
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(32).hex())
database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/school_grades')
# Heroku и некоторые хосты отдают postgres:// — SQLAlchemy требует postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Настройки сессий
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    seconds=int(os.getenv('PERMANENT_SESSION_LIFETIME', 7200))
)
session_cookie_secure_default = 'True' if IS_PRODUCTION else 'False'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', session_cookie_secure_default).lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

# Создаем папку для загрузок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Инициализация расширений
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# CSRF защита
csrf = CSRFProtect(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
)

# Security headers (включаем только в production)
if IS_PRODUCTION:
    talisman_force_https = os.getenv('FORCE_HTTPS', 'True').lower() == 'true'
    Talisman(
        app,
        force_https=talisman_force_https,
        strict_transport_security=talisman_force_https,
        strict_transport_security_max_age=31536000,
        content_security_policy={
            'default-src': "'self'",
            # NOTE: 'unsafe-inline' оставлено для совместимости с текущими шаблонами.
            'script-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            'style-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            'img-src': "'self' data: https:",
            'font-src': "'self' https://cdnjs.cloudflare.com"
        },
        frame_options='DENY',
        x_content_type_options=True,
        referrer_policy='strict-origin-when-cross-origin'
    )

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"  # Защита от session fixation

# Proxy fix (для корректной работы HTTPS/host за обратным прокси в production)
if IS_PRODUCTION and os.getenv('USE_PROXYFIX', 'True').lower() == 'true':
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=int(os.getenv('PROXYFIX_X_FOR', '1')),
        x_proto=int(os.getenv('PROXYFIX_X_PROTO', '1')),
        x_host=int(os.getenv('PROXYFIX_X_HOST', '1')),
        x_port=int(os.getenv('PROXYFIX_X_PORT', '1')),
        x_prefix=int(os.getenv('PROXYFIX_X_PREFIX', '1')),
    )

# Логирование
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'teacher', 'admin', 'employer'
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False)
    employer_profile = db.relationship('EmployerProfile', backref='user', uselist=False)
    grades = db.relationship('Grade', foreign_keys='Grade.student_id', backref='student', lazy=True)
    teacher_grades = db.relationship('Grade', foreign_keys='Grade.teacher_id', backref='teacher', lazy=True)
    token_awards = db.relationship('TokenAward', foreign_keys='TokenAward.student_id', backref='student', lazy=True)
    token_awards_given = db.relationship('TokenAward', foreign_keys='TokenAward.teacher_id', backref='teacher', lazy=True)

class StudyDirection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Specialization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Characteristic(db.Model):
    """5 характеристик для работодателя (названия настраиваются в админке)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

class SubjectCharacteristic(db.Model):
    """Влияние предмета на характеристику: коэффициент от 0 до 1."""
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    characteristic_id = db.Column(db.Integer, db.ForeignKey('characteristic.id'), nullable=False)
    coefficient = db.Column(db.Float, nullable=False, default=0)  # 0–1
    __table_args__ = (db.UniqueConstraint('subject_id', 'characteristic_id', name='uq_subject_characteristic'),)
    subject = db.relationship('Subject', backref='subject_characteristics')
    characteristic = db.relationship('Characteristic', backref='subject_characteristics')

class EmployerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    company_description = db.Column(db.Text)
    contact_person = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    address = db.Column(db.Text)
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))  # малый, средний, крупный
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    invitations_quota = db.Column(db.Integer, nullable=False, default=10)  # Лимит приглашений для работодателя

class InterviewInvitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    employer = db.relationship('User', foreign_keys=[employer_id], backref='sent_invitations')
    student = db.relationship('User', foreign_keys=[student_id], backref='received_invitations')

class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    phone = db.Column(db.String(20))
    birth_date = db.Column(db.Date)
    address = db.Column(db.Text)
    photo_filename = db.Column(db.String(255))
    study_form = db.Column(db.String(20))  # очная, заочная, дистанционная
    desired_direction_id = db.Column(db.Integer, db.ForeignKey('study_direction.id'))
    desired_specialization_id = db.Column(db.Integer, db.ForeignKey('specialization.id'))
    about_me = db.Column(db.Text)  # О себе
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    group = db.relationship('Group', backref='students')
    desired_direction = db.relationship('StudyDirection', backref='students')
    desired_specialization = db.relationship('Specialization', backref='students')

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    grade_value = db.Column(db.Integer, nullable=False)  # Звёзды 1–5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    subject = db.relationship('Subject', backref='grades')

class TokenAward(db.Model):
    """Выданный жетон студенту (накапливаются)."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token_type = db.Column(db.String(50), nullable=False)  # один из TOKEN_TYPES
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))  # при какой оценке выдан
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subject = db.relationship('Subject', backref='token_awards')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def compute_student_characteristics(student_id):
    """Вычисляет 5 характеристик (0–100) по оценкам и коэффициентам предметов."""
    from sqlalchemy import func
    grades_by_subject = db.session.query(
        Grade.subject_id,
        func.avg(Grade.grade_value).label('avg_grade')
    ).filter(Grade.student_id == student_id).group_by(Grade.subject_id).all()
    if not grades_by_subject:
        return []
    subject_avg = {s: float(a) for s, a in grades_by_subject}
    characteristics = Characteristic.query.order_by(Characteristic.sort_order, Characteristic.id).all()
    result = []
    for ch in characteristics:
        scs = SubjectCharacteristic.query.filter_by(characteristic_id=ch.id).all()
        total_coef = 0.0
        weighted_sum = 0.0
        for sc in scs:
            if sc.subject_id in subject_avg and sc.coefficient and sc.coefficient > 0:
                total_coef += sc.coefficient
                weighted_sum += (subject_avg[sc.subject_id] / 5.0) * sc.coefficient
        if total_coef > 0:
            value = round((weighted_sum / total_coef) * 100, 1)
        else:
            value = 0.0
        result.append({'id': ch.id, 'name': ch.name, 'value': value})
    return result

def get_student_token_counts(student_id):
    """Возвращает словарь {тип_жетона: количество} для студента."""
    from sqlalchemy import func
    rows = db.session.query(TokenAward.token_type, func.count(TokenAward.id)).filter(
        TokenAward.student_id == student_id
    ).group_by(TokenAward.token_type).all()
    counts = {t: 0 for t in TOKEN_TYPES}
    for token_type, cnt in rows:
        if token_type in counts:
            counts[token_type] = cnt
    return counts

# Функции для работы с файлами
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MIME_TYPES = ['image/png', 'image/jpeg', 'image/gif']
MAX_IMAGE_SIZE = (2000, 2000)  # Максимальный размер изображения

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(file):
    """Проверка, что файл действительно изображение"""
    try:
        from PIL import Image
        
        # Сохраняем позицию
        file.seek(0)
        
        # Проверка через PIL
        try:
            img = Image.open(file)
            img.verify()
        except Exception as e:
            app.logger.warning(f'Image verification failed: {e}')
            return False
        
        # Проверка размера
        file.seek(0)
        img = Image.open(file)
        if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
            app.logger.warning(f'Image too large: {img.size}')
            return False
        
        # Проверка формата
        if img.format not in ['PNG', 'JPEG', 'GIF']:
            app.logger.warning(f'Invalid image format: {img.format}')
            return False
            
        return True
    except ImportError:
        # Если PIL не установлен, пропускаем проверку (не рекомендуется)
        app.logger.warning('PIL not installed, skipping image validation')
        return True
    except Exception as e:
        app.logger.error(f'Error validating image: {e}')
        return False

def save_profile_photo(file, user_id):
    if file and allowed_file(file.filename):
        if not validate_image(file):
            raise ValueError("Файл не является валидным изображением")
        
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Сохраняем файл
        file.seek(0)
        file.save(file_path)
        
        # Дополнительная проверка после сохранения
        try:
            with open(file_path, 'rb') as f:
                if not validate_image(f):
                    os.remove(file_path)
                    raise ValueError("Файл не прошел проверку после сохранения")
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        
        app.logger.info(f'Photo uploaded for user {user_id}: {unique_filename}')
        return unique_filename
    return None

# Маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'employer':
            return redirect(url_for('employer_dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def register():
    form = RegistrationForm()
    selected_role = request.args.get('role', '')
    # Предвыбор роли при переходе с главной (карточки студент/учитель/работодатель)
    if selected_role in ('student', 'teacher', 'employer'):
        form.role.data = selected_role

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        role = form.role.data
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            return render_template('register.html', form=form, selected_role=role)
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует')
            return render_template('register.html', form=form, selected_role=role)
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_approved=(role == 'student')  # Студенты одобряются автоматически, остальные требуют одобрения
        )
        
        db.session.add(user)
        db.session.commit()
        
        app.logger.info(f'New user registered: {username} (role: {role}) from IP: {request.remote_addr}')
        flash('Регистрация успешна! Ожидайте одобрения администратора.')
        return redirect(url_for('login'))
    
    # Отображаем ошибки валидации
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}')
    
    return render_template('register.html', form=form, selected_role=selected_role)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_approved:
                login_user(user, remember=False)
                app.logger.info(f'User logged in: {username} from IP: {request.remote_addr}')
                return redirect(url_for('index'))
            else:
                app.logger.warning(f'Login attempt for unapproved user: {username} from IP: {request.remote_addr}')
                flash('Ваш аккаунт еще не одобрен администратором')
        else:
            app.logger.warning(f'Failed login attempt for username: {username} from IP: {request.remote_addr}')
            flash('Неверное имя пользователя или пароль')
    
    return render_template('login.html', form=form)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    profile = current_user.student_profile
    grades = Grade.query.filter_by(student_id=current_user.id).all()
    invitations = InterviewInvitation.query.filter_by(student_id=current_user.id).all()
    return render_template('student_dashboard.html', profile=profile, grades=grades, invitations=invitations)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student':
        flash('Доступ запрещен')
        app.logger.warning(f'Unauthorized access attempt to student_profile by user {current_user.id} (role: {current_user.role})')
        return redirect(url_for('index'))
    
    form = StudentProfileForm()
    
    if form.validate_on_submit():
        profile = current_user.student_profile
        if not profile:
            profile = StudentProfile(user_id=current_user.id)
            db.session.add(profile)
        
        profile.first_name = form.first_name.data
        profile.last_name = form.last_name.data
        profile.phone = form.phone.data if form.phone.data else None
        profile.address = form.address.data if form.address.data else None
        profile.study_form = form.study_form.data if form.study_form.data else None
        profile.about_me = form.about_me.data if form.about_me.data else None
        
        # Обработка группы
        if form.group_id.data:
            profile.group_id = form.group_id.data
        
        # Обработка направления и специализации
        if form.desired_direction_id.data:
            profile.desired_direction_id = form.desired_direction_id.data
        if form.desired_specialization_id.data:
            profile.desired_specialization_id = form.desired_specialization_id.data
        
        if form.birth_date.data:
            profile.birth_date = form.birth_date.data
        
        # Обработка загрузки фото
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                try:
                    # Удаляем старое фото если есть
                    if profile.photo_filename:
                        old_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], profile.photo_filename)
                        if os.path.exists(old_photo_path):
                            os.remove(old_photo_path)
                    
                    # Сохраняем новое фото
                    new_filename = save_profile_photo(file, current_user.id)
                    if new_filename:
                        profile.photo_filename = new_filename
                except ValueError as e:
                    flash(f'Ошибка загрузки фото: {str(e)}')
                    app.logger.warning(f'Photo upload failed for user {current_user.id}: {str(e)}')
        
        db.session.commit()
        app.logger.info(f'Student profile updated: user {current_user.id}')
        flash('Профиль успешно обновлен!')
        return redirect(url_for('student_dashboard'))
    
    # Заполняем форму текущими данными
    profile = current_user.student_profile
    if profile:
        form.first_name.data = profile.first_name
        form.last_name.data = profile.last_name
        form.phone.data = profile.phone
        form.address.data = profile.address
        form.study_form.data = profile.study_form
        form.about_me.data = profile.about_me
        form.group_id.data = profile.group_id
        form.desired_direction_id.data = profile.desired_direction_id
        form.desired_specialization_id.data = profile.desired_specialization_id
        form.birth_date.data = profile.birth_date
    
    groups = Group.query.all()
    directions = StudyDirection.query.all()
    specializations = Specialization.query.all()
    return render_template('student_profile.html', form=form, profile=profile, groups=groups, directions=directions, specializations=specializations)

@app.route('/employer/dashboard')
@login_required
def employer_dashboard():
    if current_user.role != 'employer':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    # Проверяем, заполнен ли профиль работодателя
    employer_profile = current_user.employer_profile
    has_employer_profile = employer_profile is not None
    # Счётчики приглашений
    invitations_sent_count = InterviewInvitation.query.filter_by(employer_id=current_user.id).count()
    invitations_quota = 10
    if employer_profile and employer_profile.invitations_quota is not None:
        invitations_quota = employer_profile.invitations_quota
    invitations_remaining = max(invitations_quota - invitations_sent_count, 0)

    # Получаем всех студентов с их профилями и средними оценками
    students_query = db.session.query(User, StudentProfile).join(
        StudentProfile, User.id == StudentProfile.user_id
    ).filter(User.role == 'student')
    
    # Получаем список ID студентов, которым уже было отправлено приглашение этим работодателем
    invited_student_ids = set()
    existing_invitations = InterviewInvitation.query.filter_by(employer_id=current_user.id).all()
    for invitation in existing_invitations:
        invited_student_ids.add(invitation.student_id)
    
    # Характеристики (названия для шаблона)
    characteristics_list = Characteristic.query.order_by(Characteristic.sort_order, Characteristic.id).all()
    
    # Добавляем характеристики и жетоны по студентам (оценки работодателю не показываем)
    students_with_grades = []
    students_for_js = []
    
    for user, profile in students_query.all():
        characteristics = compute_student_characteristics(user.id)
        token_counts = get_student_token_counts(user.id)
        already_invited = user.id in invited_student_ids
        
        students_with_grades.append({
            'user': user,
            'profile': profile,
            'characteristics': characteristics,
            'token_counts': token_counts,
            'already_invited': already_invited
        })
        
        students_for_js.append({
            'id': user.id,
            'name': f"{profile.first_name} {profile.last_name}" if profile else user.username,
            'study_form': profile.study_form if profile else None,
            'direction': profile.desired_direction.name if profile and profile.desired_direction else None,
            'specialization': profile.desired_specialization.name if profile and profile.desired_specialization else None,
            'birth_date': profile.birth_date.isoformat() if profile and profile.birth_date else None,
            'photo_filename': profile.photo_filename if profile else None,
            'characteristics': characteristics,
            'token_counts': token_counts,
            'already_invited': already_invited
        })
    
    return render_template(
        'employer_dashboard.html',
        students=students_with_grades,
        students_for_js=students_for_js,
        token_catalog=TOKEN_CATALOG,
        characteristics_list=characteristics_list,
        now=datetime.utcnow(),
        has_employer_profile=has_employer_profile,
        invitations_quota=invitations_quota,
        invitations_remaining=invitations_remaining,
        invitations_sent_count=invitations_sent_count
    )

@app.route('/employer/profile', methods=['GET', 'POST'])
@login_required
def employer_profile():
    if current_user.role != 'employer':
        flash('Доступ запрещен')
        app.logger.warning(f'Unauthorized access attempt to employer_profile by user {current_user.id} (role: {current_user.role})')
        return redirect(url_for('index'))
    
    form = EmployerProfileForm()
    
    if form.validate_on_submit():
        profile = current_user.employer_profile
        if not profile:
            profile = EmployerProfile(user_id=current_user.id)
            db.session.add(profile)
        
        profile.company_name = form.company_name.data
        profile.company_description = form.company_description.data if form.company_description.data else None
        profile.contact_person = form.contact_person.data
        profile.phone = form.phone.data if form.phone.data else None
        profile.email = form.email.data if form.email.data else None
        profile.website = form.website.data if form.website.data else None
        profile.address = form.address.data if form.address.data else None
        profile.industry = form.industry.data if form.industry.data else None
        profile.company_size = form.company_size.data if form.company_size.data else None
        
        db.session.commit()
        app.logger.info(f'Employer profile updated: user {current_user.id}')
        flash('Профиль компании успешно обновлен!')
        return redirect(url_for('employer_dashboard'))
    
    # Заполняем форму текущими данными
    profile = current_user.employer_profile
    if profile:
        form.company_name.data = profile.company_name
        form.company_description.data = profile.company_description
        form.contact_person.data = profile.contact_person
        form.phone.data = profile.phone
        form.email.data = profile.email
        form.website.data = profile.website
        form.address.data = profile.address
        form.industry.data = profile.industry
        form.company_size.data = profile.company_size
    
    return render_template('employer_profile.html', form=form, profile=profile)

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    # Получаем все группы студентов
    groups = Group.query.all()
    
    return render_template('teacher_dashboard.html', groups=groups)

@app.route('/teacher/grade/<int:group_id>')
@login_required
def grade_students(group_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    # Получаем группу
    group = Group.query.get_or_404(group_id)
    
    # Получаем всех студентов из группы
    students = db.session.query(User, StudentProfile).join(
        StudentProfile, User.id == StudentProfile.user_id
    ).filter(StudentProfile.group_id == group_id).all()
    
    # Получаем все предметы для выбора
    subjects = Subject.query.all()

    students_sequential = []
    for user, profile in students:
        fn = (profile.first_name or '').strip()
        parts = fn.split()
        if len(parts) >= 2 and parts[1]:
            display_name = f'{profile.last_name} {parts[0]} {parts[1][0]}.'
        else:
            display_name = f'{profile.last_name} {profile.first_name}'
        photo_url = (
            url_for('uploaded_file', filename=profile.photo_filename)
            if profile.photo_filename
            else None
        )
        students_sequential.append({
            'id': user.id,
            'name': display_name,
            'photo_url': photo_url,
        })
    
    return render_template(
        'grade_students.html',
        students=students,
        group=group,
        subjects=subjects,
        token_catalog=TOKEN_CATALOG,
        students_sequential=students_sequential,
    )

@app.route('/teacher/submit_grades', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def submit_grades():
    if current_user.role != 'teacher':
        app.logger.warning(f'Unauthorized access attempt to submit_grades by user {current_user.id} (role: {current_user.role})')
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    try:
        schema = SubmitGradesSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        app.logger.warning(f'Invalid grades data from user {current_user.id}: {err.messages}')
        return jsonify({'success': False, 'message': 'Ошибка валидации', 'errors': err.messages}), 400
    
    # Проверка существования предмета
    subject = Subject.query.get(data['subject_id'])
    if not subject:
        return jsonify({'success': False, 'message': 'Предмет не найден'}), 404
    
    # Проверка существования студентов и валидация жетонов
    for grade_data in data['grades']:
        student = User.query.get(grade_data['student_id'])
        if not student or student.role != 'student':
            return jsonify({'success': False, 'message': f'Студент {grade_data["student_id"]} не найден'}), 404
        tokens = grade_data.get('tokens') or []
        if len(tokens) > 3:
            return jsonify({'success': False, 'message': 'Не более 3 жетонов на студента'}), 400
        for t in tokens:
            if t not in TOKEN_TYPES:
                return jsonify({'success': False, 'message': f'Неизвестный тип жетона: {t}'}), 400
        
        grade = Grade(
            student_id=grade_data['student_id'],
            teacher_id=current_user.id,
            subject_id=data['subject_id'],
            grade_value=grade_data['grade'],
            comment=grade_data.get('comment', '')
        )
        db.session.add(grade)
        db.session.flush()  # чтобы grade.id был доступен
        for token_type in tokens:
            award = TokenAward(
                student_id=grade_data['student_id'],
                teacher_id=current_user.id,
                token_type=token_type,
                subject_id=data['subject_id']
            )
            db.session.add(award)
    
    db.session.commit()
    app.logger.info(f'Teacher {current_user.id} submitted grades for subject {data["subject_id"]}')
    return jsonify({'success': True, 'message': 'Оценки успешно сохранены'})

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    # Получаем всех пользователей
    users = User.query.all()
    pending_teachers = User.query.filter_by(role='teacher', is_approved=False).all()
    pending_employers = User.query.filter_by(role='employer', is_approved=False).all()
    invitations = InterviewInvitation.query.all()
    
    return render_template('admin_dashboard.html', users=users, pending_teachers=pending_teachers, pending_employers=pending_employers, invitations=invitations)


@app.route('/admin/employers')
@login_required
def admin_employers():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))

    # Все пользователи-работодатели
    employers_q = User.query.filter_by(role='employer').all()

    items = []
    for employer in employers_q:
        profile = employer.employer_profile
        sent_count = InterviewInvitation.query.filter_by(employer_id=employer.id).count()
        items.append({'user': employer, 'profile': profile, 'sent_count': sent_count})

    return render_template('admin_employers.html', employers=items)

@app.route('/admin/approve_teacher/<int:user_id>', methods=['POST'])
@login_required
def approve_teacher(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        app.logger.warning(f'Unauthorized access attempt to approve_teacher by user {current_user.id} (role: {current_user.role})')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    app.logger.info(f'Admin {current_user.id} approved teacher {user_id} ({user.username})')
    flash(f'Учитель {user.username} одобрен')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_employer/<int:user_id>', methods=['POST'])
@login_required
def approve_employer(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        app.logger.warning(f'Unauthorized access attempt to approve_employer by user {current_user.id} (role: {current_user.role})')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    app.logger.info(f'Admin {current_user.id} approved employer {user_id} ({user.username})')
    flash(f'Работодатель {user.username} одобрен')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/employer_quota/<int:user_id>', methods=['POST'])
@login_required
def update_employer_quota(user_id):
    """Обновление лимита приглашений для работодателя."""
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        app.logger.warning(f'Unauthorized access attempt to update_employer_quota by user {current_user.id} (role: {current_user.role})')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    if user.role != 'employer':
        flash('Лимит приглашений можно задавать только для работодателей')
        return redirect(url_for('admin_dashboard'))

    raw_quota = (request.form.get('invitations_quota') or '').strip()
    try:
        quota = int(raw_quota)
    except ValueError:
        quota = 10

    if quota < 0:
        quota = 0

    profile = user.employer_profile
    if not profile:
        profile = EmployerProfile(user_id=user.id, company_name=user.username, contact_person=user.username)
        db.session.add(profile)

    profile.invitations_quota = quota
    db.session.commit()

    app.logger.info(f'Admin {current_user.id} set invitations_quota={quota} for employer {user_id} ({user.username})')
    flash(f'Лимит приглашений для работодателя {user.username} обновлён (теперь {quota})')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        app.logger.warning(f'Unauthorized access attempt to delete_user by user {current_user.id} (role: {current_user.role})')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    username = user.username  # Сохраняем имя для сообщения
    
    # Удаляем жетоны (где пользователь студент или учитель)
    TokenAward.query.filter(db.or_(TokenAward.student_id == user_id, TokenAward.teacher_id == user_id)).delete(synchronize_session=False)
    # Удаляем все оценки, где пользователь является учителем
    teacher_grades = Grade.query.filter_by(teacher_id=user_id).all()
    for grade in teacher_grades:
        db.session.delete(grade)
    # Удаляем все оценки, где пользователь является студентом
    student_grades = Grade.query.filter_by(student_id=user_id).all()
    for grade in student_grades:
        db.session.delete(grade)
    # Удаляем профиль студента и его фото
    if user.student_profile:
        if user.student_profile.photo_filename:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], user.student_profile.photo_filename)
            if os.path.exists(photo_path):
                os.remove(photo_path)
        db.session.delete(user.student_profile)
    
    # Удаляем профиль работодателя
    if user.employer_profile:
        db.session.delete(user.employer_profile)
    
    # Удаляем приглашения, где пользователь является работодателем
    sent_invitations = InterviewInvitation.query.filter_by(employer_id=user_id).all()
    for invitation in sent_invitations:
        db.session.delete(invitation)
    
    # Удаляем приглашения, где пользователь является студентом
    received_invitations = InterviewInvitation.query.filter_by(student_id=user_id).all()
    for invitation in received_invitations:
        db.session.delete(invitation)
    
    # Теперь можно безопасно удалить пользователя
    db.session.delete(user)
    db.session.commit()
    
    app.logger.warning(f'Admin {current_user.id} deleted user {user_id} ({username})')
    flash(f'Пользователь {username} удален')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/directions')
@login_required
def admin_directions():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    directions = StudyDirection.query.all()
    return render_template('admin_directions.html', directions=directions)

@app.route('/admin/directions/add', methods=['POST'])
@login_required
def add_direction():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    name = request.form.get('name')
    if name:
        direction = StudyDirection(name=name)
        db.session.add(direction)
        db.session.commit()
        flash(f'Направление "{name}" добавлено')
    else:
        flash('Название направления не может быть пустым')
    
    return redirect(url_for('admin_directions'))

@app.route('/admin/directions/delete/<int:direction_id>', methods=['POST'])
@login_required
def delete_direction(direction_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    direction = StudyDirection.query.get_or_404(direction_id)
    db.session.delete(direction)
    db.session.commit()
    
    flash(f'Направление "{direction.name}" удалено')
    return redirect(url_for('admin_directions'))

@app.route('/admin/specializations')
@login_required
def admin_specializations():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    specializations = Specialization.query.all()
    return render_template('admin_specializations.html', specializations=specializations)

@app.route('/admin/specializations/add', methods=['POST'])
@login_required
def add_specialization():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    name = request.form.get('name')
    if name:
        specialization = Specialization(name=name)
        db.session.add(specialization)
        db.session.commit()
        flash(f'Специализация "{name}" добавлена')
    else:
        flash('Название специализации не может быть пустым')
    
    return redirect(url_for('admin_specializations'))

@app.route('/admin/specializations/delete/<int:specialization_id>', methods=['POST'])
@login_required
def delete_specialization(specialization_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    specialization = Specialization.query.get_or_404(specialization_id)
    db.session.delete(specialization)
    db.session.commit()
    
    flash(f'Специализация "{specialization.name}" удалена')
    return redirect(url_for('admin_specializations'))

@app.route('/admin/groups')
@login_required
def admin_groups():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    groups = Group.query.all()
    return render_template('admin_groups.html', groups=groups)

@app.route('/admin/groups/add', methods=['POST'])
@login_required
def add_group():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    name = request.form.get('name')
    if name:
        group = Group(name=name)
        db.session.add(group)
        db.session.commit()
        flash(f'Группа "{name}" добавлена')
    else:
        flash('Название группы не может быть пустым')
    
    return redirect(url_for('admin_groups'))

@app.route('/admin/groups/delete/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    
    flash(f'Группа "{group.name}" удалена')
    return redirect(url_for('admin_groups'))

@app.route('/admin/subjects')
@login_required
def admin_subjects():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    subjects = Subject.query.all()
    return render_template('admin_subjects.html', subjects=subjects)

@app.route('/admin/subjects/add', methods=['POST'])
@login_required
def add_subject():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    name = request.form.get('name')
    if name:
        subject = Subject(name=name)
        db.session.add(subject)
        db.session.commit()
        flash(f'Предмет "{name}" добавлен')
    else:
        flash('Название предмета не может быть пустым')
    
    return redirect(url_for('admin_subjects'))

@app.route('/admin/subjects/delete/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    subject = Subject.query.get_or_404(subject_id)
    name = subject.name
    SubjectCharacteristic.query.filter_by(subject_id=subject_id).delete(synchronize_session=False)
    TokenAward.query.filter_by(subject_id=subject_id).delete(synchronize_session=False)
    db.session.delete(subject)
    db.session.commit()
    
    flash(f'Предмет "{name}" удален')
    return redirect(url_for('admin_subjects'))

@app.route('/admin/characteristics', methods=['GET', 'POST'])
@login_required
def admin_characteristics():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    characteristics = Characteristic.query.order_by(Characteristic.sort_order, Characteristic.id).all()
    if request.method == 'POST':
        for ch in characteristics:
            key = f'name_{ch.id}'
            if key in request.form:
                ch.name = (request.form.get(key) or '').strip() or ch.name
        db.session.commit()
        flash('Названия характеристик сохранены')
        return redirect(url_for('admin_characteristics'))
    return render_template('admin_characteristics.html', characteristics=characteristics)

@app.route('/admin/subject_characteristics', methods=['GET', 'POST'])
@login_required
def admin_subject_characteristics():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    subjects = Subject.query.all()
    characteristics = Characteristic.query.order_by(Characteristic.sort_order, Characteristic.id).all()
    if request.method == 'POST':
        for s in subjects:
            for ch in characteristics:
                key = f'coef_{s.id}_{ch.id}'
                if key in request.form:
                    try:
                        val = float(request.form.get(key).replace(',', '.'))
                        val = max(0, min(1, val))
                    except (ValueError, TypeError):
                        val = 0
                    sc = SubjectCharacteristic.query.filter_by(subject_id=s.id, characteristic_id=ch.id).first()
                    if sc:
                        sc.coefficient = val
                    else:
                        sc = SubjectCharacteristic(subject_id=s.id, characteristic_id=ch.id, coefficient=val)
                        db.session.add(sc)
        db.session.commit()
        flash('Коэффициенты влияния предметов на характеристики сохранены')
        return redirect(url_for('admin_subject_characteristics'))
    sc_list = SubjectCharacteristic.query.all()
    coef_map = {(sc.subject_id, sc.characteristic_id): sc.coefficient for sc in sc_list}
    return render_template('admin_subject_characteristics.html', subjects=subjects, characteristics=characteristics, coef_map=coef_map)

@app.route('/employer/send_invitation', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def send_invitation():
    if current_user.role != 'employer':
        app.logger.warning(f'Unauthorized access attempt to send_invitation by user {current_user.id} (role: {current_user.role})')
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    # Запрет отправки приглашений без заполненного профиля работодателя
    employer_profile = current_user.employer_profile
    if not employer_profile:
        app.logger.warning(f'Employer {current_user.id} attempted to send invitation without employer profile')
        return jsonify({'success': False, 'message': 'Сначала заполните профиль компании'}), 400

    # Проверка лимита приглашений
    invitations_quota = employer_profile.invitations_quota or 10
    invitations_sent_count = InterviewInvitation.query.filter_by(employer_id=current_user.id).count()
    if invitations_sent_count >= invitations_quota:
        app.logger.warning(f'Employer {current_user.id} exceeded invitations quota ({invitations_sent_count}/{invitations_quota})')
        return jsonify({
            'success': False,
            'message': f'Исчерпан лимит приглашений ({invitations_sent_count} из {invitations_quota}). Обратитесь к администратору.'
        }), 400
    
    try:
        schema = InvitationSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        app.logger.warning(f'Invalid invitation data from user {current_user.id}: {err.messages}')
        return jsonify({'success': False, 'message': 'Ошибка валидации', 'errors': err.messages}), 400
    
    # Проверка существования студента
    student = User.query.get(data['student_id'])
    if not student or student.role != 'student':
        return jsonify({'success': False, 'message': 'Студент не найден'}), 404
    
    # Проверка на дубликаты
    existing_invitation = InterviewInvitation.query.filter_by(
        employer_id=current_user.id,
        student_id=data['student_id'],
        status='pending'
    ).first()
    
    if existing_invitation:
        return jsonify({'success': False, 'message': 'Приглашение уже отправлено этому студенту'})
    
    invitation = InterviewInvitation(
        employer_id=current_user.id,
        student_id=data['student_id'],
        position=data['position'],
        message=data.get('message', '')
    )
    
    db.session.add(invitation)
    db.session.commit()
    app.logger.info(f'Employer {current_user.id} sent invitation to student {data["student_id"]}')
    return jsonify({'success': True, 'message': 'Приглашение успешно отправлено'})

@app.route('/student/respond_invitation/<int:invitation_id>', methods=['POST'])
@login_required
def respond_invitation(invitation_id):
    if current_user.role != 'student':
        flash('Доступ запрещен')
        app.logger.warning(f'Unauthorized access attempt to respond_invitation by user {current_user.id} (role: {current_user.role})')
        return redirect(url_for('index'))
    
    status = (request.form.get('status') or '').strip()

    # Безопасная проверка - приглашение должно принадлежать текущему пользователю
    invitation = InterviewInvitation.query.filter_by(
        id=invitation_id,
        student_id=current_user.id
    ).first_or_404()
    
    if status in ['accepted', 'declined']:
        invitation.status = status
        db.session.commit()
        app.logger.info(f'Student {current_user.id} {status} invitation {invitation_id}')
        
        status_text = 'принято' if status == 'accepted' else 'отклонено'
        flash(f'Приглашение {status_text}')
    else:
        flash('Неверный статус')
        app.logger.warning(f'Invalid status in respond_invitation: {status} by user {current_user.id}')
    
    return redirect(url_for('student_dashboard'))

@app.route('/employer/invitations')
@login_required
def employer_invitations():
    if current_user.role != 'employer':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    
    # Получаем все приглашения, отправленные этим работодателем
    invitations = InterviewInvitation.query.filter_by(employer_id=current_user.id).order_by(InterviewInvitation.created_at.desc()).all()

    # Счётчики приглашений
    employer_profile = current_user.employer_profile
    invitations_sent_count = len(invitations)
    invitations_quota = 10
    if employer_profile and employer_profile.invitations_quota is not None:
        invitations_quota = employer_profile.invitations_quota
    invitations_remaining = max(invitations_quota - invitations_sent_count, 0)
    
    return render_template(
        'employer_invitations.html',
        invitations=invitations,
        invitations_quota=invitations_quota,
        invitations_remaining=invitations_remaining,
        invitations_sent_count=invitations_sent_count
    )


@app.route('/docs/privacy')
def privacy_policy():
    return render_template('docs/privacy_policy.html')


@app.route('/docs/terms')
def terms_of_use():
    return render_template('docs/terms_of_use.html')


@app.route('/docs/personal-data-consent')
def personal_data_consent():
    return render_template('docs/personal_data_consent.html')


@app.route('/docs/site-rules')
def site_rules():
    return render_template('docs/site_rules.html')

# Обработка ошибок
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'Internal server error: {error}', exc_info=True)
    if app.debug:
        return str(error), 500
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    app.logger.warning(f'Forbidden access: {request.url} from IP: {request.remote_addr}')
    flash('Доступ запрещен')
    return redirect(url_for('index')), 403

@app.route('/admin/student-profile/<int:user_id>')
@login_required
def admin_student_profile(user_id):
    """API endpoint для получения полной информации о профиле студента для админ панели"""
    # Проверяем, что пользователь - админ
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
    
    # Получаем пользователя
    user = User.query.get_or_404(user_id)
    
    # Проверяем, что это студент
    if user.role != 'student':
        return jsonify({'success': False, 'error': 'Пользователь не является студентом'}), 400
    
    # Получаем профиль студента
    profile = user.student_profile
    if not profile:
        return jsonify({'success': False, 'error': 'Профиль студента не найден'}), 404
    
    # Получаем оценки студента с информацией о предметах и учителях
    grades = Grade.query.filter_by(student_id=user_id)\
                      .join(Subject, Grade.subject_id == Subject.id)\
                      .join(User, Grade.teacher_id == User.id)\
                      .add_columns(Subject.name.label('subject_name'), User.username.label('teacher_username'))\
                      .order_by(Grade.created_at.desc())\
                      .all()
    
    # Формируем данные для JSON
    student_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'profile': {
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'phone': profile.phone,
            'birth_date': profile.birth_date.isoformat() if profile.birth_date else None,
            'address': profile.address,
            'photo_filename': profile.photo_filename,
            'study_form': profile.study_form,
            'about_me': profile.about_me,
            'group': {
                'name': profile.group.name if profile.group else None
            } if profile.group else None,
            'direction': {
                'name': profile.desired_direction.name if profile.desired_direction else None
            } if profile.desired_direction else None,
            'specialization': {
                'name': profile.desired_specialization.name if profile.desired_specialization else None
            } if profile.desired_specialization else None
        },
        'grades': [
            {
                'id': grade.id,
                'grade': grade.grade_value,
                'created_at': grade.created_at.isoformat(),
                'subject': {
                    'name': grade.subject_name
                },
                'teacher': {
                    'username': grade.teacher_username
                }
            }
            for grade in grades
        ]
    }
    
    return jsonify({'success': True, 'student': student_data})

if __name__ == '__main__':
    with app.app_context():
        # Опциональный bootstrap данных для DEV/первого запуска.
        # В production не включать!
        if os.getenv('BOOTSTRAP_DATA', 'False').lower() == 'true':
            # Создаем админа (только если задан пароль в env)
            admin_username = os.getenv('BOOTSTRAP_ADMIN_USERNAME', 'admin')
            admin_email = os.getenv('BOOTSTRAP_ADMIN_EMAIL', 'admin@school.com')
            admin_password = os.getenv('BOOTSTRAP_ADMIN_PASSWORD', '')

            if admin_password:
                admin = User.query.filter_by(username=admin_username).first()
                if not admin:
                    admin = User(
                        username=admin_username,
                        email=admin_email,
                        password_hash=generate_password_hash(admin_password),
                        role='admin',
                        is_approved=True
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print(f"Создан админ: username={admin_username}, password=<set via env>")
            else:
                print("BOOTSTRAP_DATA=True, но BOOTSTRAP_ADMIN_PASSWORD не задан — админ не создан.")

            # Добавляем начальные направления
            if StudyDirection.query.count() == 0:
                directions = [
                    'Строительство',
                    'Проектирование',
                    'Эксплуатация',
                    'Контроль качества',
                    'Управление проектами'
                ]
                for direction_name in directions:
                    direction = StudyDirection(name=direction_name)
                    db.session.add(direction)

            # Добавляем начальные специализации
            if Specialization.query.count() == 0:
                specializations = [
                    'Мосты',
                    'Дороги',
                    'Здания',
                    'Тоннели',
                    'Аэропорты',
                    'Порты',
                    'Железные дороги'
                ]
                for spec_name in specializations:
                    specialization = Specialization(name=spec_name)
                    db.session.add(specialization)

            # Добавляем начальные группы
            if Group.query.count() == 0:
                groups = [
                    'ИС-21',
                    'ИС-22',
                    'ПИ-21',
                    'ПИ-22',
                    'МТ-21',
                    'МТ-22',
                    'СТ-21',
                    'СТ-22'
                ]
                for group_name in groups:
                    group = Group(name=group_name)
                    db.session.add(group)

            # Добавляем начальные предметы
            if Subject.query.count() == 0:
                subjects = [
                    'Математика',
                    'Физика',
                    'Химия',
                    'Информатика',
                    'Программирование',
                    'Базы данных',
                    'Сетевые технологии',
                    'Веб-разработка',
                    'Алгоритмы и структуры данных',
                    'Системный анализ',
                    'Проектирование ПО',
                    'Тестирование ПО'
                ]
                for subject_name in subjects:
                    subject = Subject(name=subject_name)
                    db.session.add(subject)

            # 5 характеристик для работодателя (названия редактируются в админке)
            if Characteristic.query.count() == 0:
                for i, name in enumerate(['Характеристика 1', 'Характеристика 2', 'Характеристика 3', 'Характеристика 4', 'Характеристика 5']):
                    ch = Characteristic(name=name, sort_order=i)
                    db.session.add(ch)

            db.session.commit()
    
    # Запуск приложения с проверкой режима отладки
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    if debug_mode:
        app.logger.warning('⚠️  ВНИМАНИЕ: Приложение запущено в режиме отладки!')
    
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
