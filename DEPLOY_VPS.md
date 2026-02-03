# Полный гайд: развёртывание на VPS по SSH

Пошаговая инструкция по запуску проекта «Система оценок для школы» на VPS-сервере (Ubuntu/Debian) с помощью SSH-команд.

---

## Содержание

1. [Требования](#1-требования)
2. [Подключение к VPS](#2-подключение-к-vps)
3. [Подготовка сервера](#3-подготовка-сервера)
4. [Установка зависимостей](#4-установка-зависимостей)
5. [PostgreSQL](#5-postgresql)
6. [Размещение проекта](#6-размещение-проекта)
7. [Виртуальное окружение и приложение](#7-виртуальное-окружение-и-приложение)
8. [Переменные окружения](#8-переменные-окружения)
9. [Миграции и первый запуск](#9-миграции-и-первый-запуск)
10. [Gunicorn и systemd](#10-gunicorn-и-systemd)
11. [Nginx (reverse proxy)](#11-nginx-reverse-proxy)
12. [SSL (HTTPS)](#12-ssl-https)
13. [Файрвол и порты](#13-файрвол-и-порты)
14. [Первый администратор](#14-первый-администратор)
15. [Проверка и обслуживание](#15-проверка-и-обслуживание)
16. [Решение проблем](#16-решение-проблем)

---

## 1. Требования

- **VPS**: Ubuntu 22.04 LTS или 24.04 LTS (или Debian 11/12) с доступом по SSH.
- **Ресурсы**: минимум 1 GB RAM, 1 vCPU, 10 GB диска (рекомендуется 2 GB RAM для production).
- **Доступ**: root или пользователь с sudo.
- **Домен** (опционально, но желательно для HTTPS): например `university-grades.ru`.

---

## 2. Подключение к VPS

С локального компьютера:

```bash
# Замените IP_ADDRESS на IP вашего VPS, user — на имя пользователя (часто root)
ssh user@IP_ADDRESS

# Или с указанием ключа
ssh -i ~/.ssh/your_key user@IP_ADDRESS
```

После входа вы находитесь в домашней директории пользователя на сервере.

---

## 3. Подготовка сервера

Обновление системы и установка базовых пакетов:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git build-essential
```

---

## 4. Установка зависимостей

### 4.1. Python 3.10+

```bash
# Проверить версию (должна быть 3.10+)
python3 --version

# Если версия старая (Ubuntu 22.04 обычно уже 3.10):
sudo apt install -y python3 python3-pip python3-venv
```

### 4.2. PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 4.3. Nginx (для reverse proxy и статики)

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
```

---

## 5. PostgreSQL

### 5.1. Создать пользователя и базу

```bash
sudo -u postgres psql
```

В консоли PostgreSQL выполните (подставьте свои логин/пароль и имя БД):

```sql
CREATE USER school_app WITH PASSWORD 'ваш_надёжный_пароль';
CREATE DATABASE school_grades OWNER school_app;
\q
```

### 5.2. (Опционально) Разрешить подключение с localhost

Обычно для приложения на том же сервере достаточно `localhost`. Если нужно подключаться с другого хоста — настройте `pg_hba.conf` и `postgresql.conf` (в данной инструкции не рассматривается).

---

## 6. Размещение проекта

### Вариант A: Клонирование из Git

```bash
# Создать директорию для приложения (например, от имени отдельного пользователя appuser)
sudo useradd -m -s /bin/bash appuser
sudo mkdir -p /var/www/school-grades
sudo chown appuser:appuser /var/www/school-grades

# Переключиться на пользователя приложения или использовать sudo -u appuser
sudo -u appuser git clone https://github.com/ВАШ_РЕПОЗИТОРИЙ/school-grades.git /var/www/school-grades
```

Если репозиторий приватный — настройте SSH-ключ для `appuser` или используйте токен в URL.

### Вариант B: Загрузка архива по SCP

На **локальном** компьютере (в каталоге проекта):

```bash
# Создать архив без venv и .env
tar --exclude='venv' --exclude='.env' --exclude='__pycache__' --exclude='.git' -czvf school-grades.tar.gz .

# Загрузить на сервер
scp school-grades.tar.gz user@IP_ADDRESS:/tmp/
```

На **сервере**:

```bash
sudo mkdir -p /var/www/school-grades
sudo tar -xzvf /tmp/school-grades.tar.gz -C /var/www/school-grades
sudo chown -R appuser:appuser /var/www/school-grades
rm /tmp/school-grades.tar.gz
```

### Итог

Проект должен лежать в `/var/www/school-grades` (или по вашему пути), внутри: `app.py`, `wsgi.py`, `requirements.txt`, `migrations/`, `templates/`, `static/` и т.д.

---

## 7. Виртуальное окружение и приложение

Все команды — из каталога проекта, от пользователя, который будет запускать приложение (например `appuser`):

```bash
cd /var/www/school-grades

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

Проверка:

```bash
# Должен быть путь к venv в приглашении
which python
which gunicorn
```

---

## 8. Переменные окружения

Создать `.env` на сервере (не копировать реальный `.env` с разработки):

```bash
cd /var/www/school-grades
nano .env
```

Вставить (и заменить значения на свои):

```env
APP_ENV=production
FLASK_DEBUG=False

SECRET_KEY=сюда_вставить_длинный_случайный_ключ

DATABASE_URL=postgresql://school_app:ваш_надёжный_пароль@localhost:5432/school_grades

SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=7200

FORCE_HTTPS=True
USE_PROXYFIX=True
PROXYFIX_X_FOR=1
PROXYFIX_X_PROTO=1
PROXYFIX_X_HOST=1
PROXYFIX_X_PORT=1
PROXYFIX_X_PREFIX=1

RATELIMIT_STORAGE_URI=memory://
BOOTSTRAP_DATA=False
```

Сгенерировать `SECRET_KEY` на сервере:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Вставьте вывод в `SECRET_KEY=` в `.env`. Сохраните файл (в nano: Ctrl+O, Enter, Ctrl+X).

Права (чтобы не светить .env лишним пользователям):

```bash
chmod 600 .env
```

---

## 9. Миграции и первый запуск

В каталоге проекта с активированным `venv`:

```bash
cd /var/www/school-grades
source venv/bin/activate
export $(grep -v '^#' .env | xargs)

# Применить миграции
python -m flask db upgrade
```

Создать каталоги, которые создаёт приложение (на всякий случай):

```bash
mkdir -p static/uploads logs
# Если запуск от root — вернуть владельца
# sudo chown -R appuser:appuser static/uploads logs
```

Проверка запуска (вручную):

```bash
gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app
```

**Важно:** приложение слушает только **127.0.0.1** — с вашего компьютера по ссылке `http://IP_СЕРВЕРА:8000` сайт **не откроется**. Это нормально: на этом этапе проверка только с самого сервера.

- Откройте **второе окно/вкладку SSH** и выполните: `curl http://127.0.0.1:8000`
- Если в ответ приходит HTML — всё работает. Остановите gunicorn в первом окне (Ctrl+C) и переходите к systemd.
- Сайт в браузере появится **после настройки Nginx** (шаг 11), по адресу `http://ваш-домен` или `http://IP_СЕРВЕРА`.

### Если сайт не виден даже через curl (127.0.0.1:8000)

1. **Порт занят или не тот** — в первом окне gunicorn не должно быть ошибки `Address already in use`. Проверьте, что в команде порт **8000** (как в curl).
2. **Ошибки в терминале** — смотрите вывод gunicorn: импорт (ModuleNotFoundError), ошибки БД, отсутствие `.env` или `SECRET_KEY`. Исправьте по сообщению.
3. **Виртуальное окружение** — команду gunicorn запускайте из каталога проекта с активированным venv: `source venv/bin/activate`, затем `gunicorn ...`.
4. **Переменные окружения** — приложение читает `.env` из текущей директории. Запускайте gunicorn из `/var/www/school-grades`: `cd /var/www/school-grades`, затем команда выше.
5. **Проверить, что процесс слушает порт:** в другом SSH выполните `ss -tlnp | grep 8000` — должна быть строка с 127.0.0.1:8000.

---

## 10. Gunicorn и systemd

Создать systemd-юнит, чтобы приложение поднималось после перезагрузки и перезапускалось при падении.

```bash
sudo nano /etc/systemd/system/school-grades.service
```

Содержимое (путь и пользователь при необходимости замените):

```ini
[Unit]
Description=School Grades Flask App (Gunicorn)
After=network.target postgresql.service

[Service]
User=appuser
Group=appuser
WorkingDirectory=/var/www/school-grades
Environment="PATH=/var/www/school-grades/venv/bin"
ExecStart=/var/www/school-grades/venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Включить и запустить:

```bash
sudo systemctl daemon-reload
sudo systemctl enable school-grades
sudo systemctl start school-grades
sudo systemctl status school-grades
```

Проверка: `curl http://127.0.0.1:8000` — должен отдаваться сайт.

---

## 11. Nginx (reverse proxy)

Nginx принимает запросы на 80/443 и отдаёт их на Gunicorn (127.0.0.1:8000), раздаёт статику.

```bash
sudo nano /etc/nginx/sites-available/school-grades
```

Пример конфига (замените `university-grades.ru` на ваш домен или IP):

```nginx
server {
    listen 80;
    server_name university-grades.ru;

    client_max_body_size 16M;

    location /static/ {
        alias /var/www/school-grades/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Активация сайта и проверка:

```bash
sudo ln -s /etc/nginx/sites-available/school-grades /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Откройте в браузере: `http://university-grades.ru` (или `http://IP_ADDRESS`). Должна открыться главная страница приложения.

---

## 12. SSL (HTTPS)

Рекомендуется для production. Используем Let's Encrypt (certbot).

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d university-grades.ru
```

Следуйте подсказкам (email, согласие с условиями). Certbot сам настроит Nginx на HTTPS и редирект с HTTP.

Проверка автообновления сертификата:

```bash
sudo certbot renew --dry-run
```

После этого в приложении уже должны быть включены `FORCE_HTTPS=True` и `SESSION_COOKIE_SECURE=True` из `.env`.

---

## 13. Файрвол и порты

Оставить открытыми только 22 (SSH), 80 (HTTP), 443 (HTTPS). Порт 8000 не открывать наружу.

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
sudo ufw status
```

---

## 14. Первый администратор

Админ по умолчанию не создаётся в production (`BOOTSTRAP_DATA=False`).

**Способ 1 — временно включить bootstrap (только на первый запуск):**

В `.env` на сервере один раз:

```env
BOOTSTRAP_DATA=True
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_EMAIL=admin@school.com
BOOTSTRAP_ADMIN_PASSWORD=QWEasd123
```

Перезапустить приложение:

```bash
sudo systemctl restart school-grades
```

Зайти в систему под admin, затем в `.env` снова выставить `BOOTSTRAP_DATA=False` и снова `sudo systemctl restart school-grades`.

**Способ 2 — создать админа вручную в БД или скриптом** (без изменения кода можно через `flask shell` и создание пользователя с ролью admin — при необходимости можно описать отдельно).

---

## 15. Проверка и обслуживание

### Логи приложения

```bash
sudo journalctl -u school-grades -f
# или
tail -f /var/www/school-grades/logs/app.log
```

### Перезапуск приложения

```bash
sudo systemctl restart school-grades
```

### Обновление кода (при деплое через Git)

```bash
cd /var/www/school-grades
sudo -u appuser git pull
source venv/bin/activate
pip install -r requirements.txt
python -m flask db upgrade
sudo systemctl restart school-grades
```

### Бэкап PostgreSQL

```bash
sudo -u postgres pg_dump school_grades > /tmp/school_grades_$(date +%Y%m%d).sql
# Перенести /tmp/... в безопасное место и удалить с сервера при необходимости
```

---

## 16. Решение проблем

### 502 Bad Gateway

- Gunicorn не запущен: `sudo systemctl status school-grades`, при необходимости `sudo systemctl start school-grades`.
- Смотреть логи: `sudo journalctl -u school-grades -n 100`.
- Проверить, что приложение слушает порт: `ss -tlnp | grep 8000`.

### Ошибки миграций / БД

- Проверить `DATABASE_URL` в `.env` и доступ PostgreSQL: `psql "$DATABASE_URL" -c "SELECT 1;"`.
- При «out of sync»: `python -m flask db stamp head`, затем при необходимости заново применить миграции.

### Нет статики / 404 на /static/

- Проверить права: `ls -la /var/www/school-grades/static/`.
- В Nginx `location /static/` должен указывать на полный путь к каталогу `static` приложения.

### Ошибки прав (Permission denied)

- Владелец файлов в `/var/www/school-grades` должен совпадать с `User=` в unit (например `appuser`):  
  `sudo chown -R appuser:appuser /var/www/school-grades`

### Слишком много запросов (rate limit)

- В production при нескольких воркерах лучше использовать Redis: установить Redis, в `.env` задать `RATELIMIT_STORAGE_URI=redis://localhost:6379/0` и перезапустить приложение.

---

## Краткая шпаргалка команд (по порядку)

```bash
# 1) Подключение
ssh user@IP_ADDRESS

# 2) Система и пакеты
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git build-essential python3 python3-pip python3-venv postgresql postgresql-contrib nginx

# 3) PostgreSQL
sudo -u postgres psql -c "CREATE USER school_app WITH PASSWORD 'PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE school_grades OWNER school_app;"

# 4) Проект в /var/www/school-grades, затем:
cd /var/www/school-grades
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 5) .env (nano .env) — заполнить SECRET_KEY, DATABASE_URL и production-настройки

# 6) Миграции
python -m flask db upgrade

# 7) Systemd (файл /etc/systemd/system/school-grades.service)
sudo systemctl enable --now school-grades

# 8) Nginx (sites-available/school-grades), затем:
sudo nginx -t && sudo systemctl reload nginx

# 9) SSL
sudo certbot --nginx -d university-grades.ru

# 10) Файрвол
sudo ufw allow 22,80,443 && sudo ufw enable
```

После выполнения всех шагов приложение будет доступно по HTTPS на вашем домене (или по IP по HTTP) и будет автоматически запускаться после перезагрузки сервера.
