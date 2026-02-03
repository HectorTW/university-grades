# 📖 Справочник команд

Полный справочник всех команд для работы с проектом.

---

## 🚀 Установка и настройка

### Создание виртуального окружения

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Активировать (Linux/Mac)
source venv/bin/activate

# Деактивировать
deactivate
```

### Установка зависимостей

```bash
# Установить все зависимости
pip install -r requirements.txt

# Обновить зависимости
pip install --upgrade -r requirements.txt

# Проверить установленные пакеты
pip list
```

### Настройка переменных окружения

```bash
# Создать файл .env (если еще не создан)
# Скопируйте пример и заполните значения

# Генерация SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Или через OpenSSL
openssl rand -hex 32
```

---

## 🏃 Запуск приложения

### Запуск в режиме разработки

```bash
# Установите FLASK_DEBUG=True в .env
python app.py

# Приложение будет доступно по адресу:
# http://localhost:5000
```

### Запуск в production режиме

```bash
# Установите FLASK_DEBUG=False в .env
# Установите SESSION_COOKIE_SECURE=True (требует HTTPS)
python app.py

# Или используйте WSGI сервер (например, Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 🗄️ Работа с миграциями базы данных

### Основные команды

```bash
# Создать миграцию после изменения моделей
python -m flask db migrate -m "Описание изменений"

# Примеры сообщений:
python -m flask db migrate -m "Add phone field to user"
python -m flask db migrate -m "Add news table"
python -m flask db migrate -m "Increase phone field length"

# Применить миграцию
python -m flask db upgrade

# Откатить последнюю миграцию
python -m flask db downgrade

# Откатить на несколько версий назад
python -m flask db downgrade -3  # Откатить на 3 версии
```

### Просмотр информации

```bash
# Посмотреть текущую версию базы данных
python -m flask db current

# Посмотреть историю всех миграций
python -m flask db history

# Показать SQL, который будет выполнен (без применения)
python -m flask db upgrade --sql

# Показать SQL для отката
python -m flask db downgrade --sql

# Получить помощь по командам
python -m flask db --help
```

### Работа с существующей базой данных

```bash
# Если у вас уже есть база данных с данными
# Отметьте текущее состояние как baseline
python -m flask db stamp head

# Это позволит применять будущие миграции на существующую БД
```

### Устранение проблем с миграциями

```bash
# Если база данных "out of sync"
python -m flask db stamp head

# Если возник конфликт миграций
# 1. Проверьте текущую версию
python -m flask db current

# 2. Откатитесь на рабочую версию
python -m flask db downgrade -1

# 3. Проверьте историю
python -m flask db history

# 4. Создайте новую миграцию
python -m flask db migrate -m "Fix migration conflict"
python -m flask db upgrade
```

---

## 🔒 Команды безопасности

### Проверка зависимостей на уязвимости

```bash
# Установить инструменты проверки
pip install safety pip-audit

# Проверка через safety
safety check

# Проверка через pip-audit (с увеличенным лимитом запросов)
pip-audit --rate-limit 20

# Проверка через Snyk (требует npm)
npm install -g snyk
snyk test --file=requirements.txt
```

### Генерация секретных ключей

```bash
# Генерация SECRET_KEY (Python)
python -c "import secrets; print(secrets.token_hex(32))"

# Генерация SECRET_KEY (OpenSSL)
openssl rand -hex 32

# Генерация SECRET_KEY (Python urandom)
python -c "import os; print(os.urandom(32).hex())"
```

### Тестирование CSRF защиты

```bash
# Попытка POST без CSRF токена (должна быть ошибка)
curl -X POST http://localhost:5000/register \
  -d "username=test&email=test@test.com&password=Test1234&role=student"

# Ожидаемый результат: ошибка CSRF
```

### Тестирование Rate Limiting

```bash
# Попытка входа 10 раз подряд (должен сработать лимит после 5)
for i in {1..10}; do
  curl -X POST http://localhost:5000/login \
    -d "username=wrong&password=wrong"
done

# Ожидаемый результат: HTTP 429 после 5 попыток
```

### Проверка Security Headers

```bash
# Проверка заголовков безопасности
curl -I http://localhost:5000

# Должны присутствовать:
# - X-Frame-Options
# - Content-Security-Policy
# - Strict-Transport-Security
# - X-Content-Type-Options
```

---

## 🧪 Тестирование

### Запуск тестов безопасности

```bash
# Если есть test_security.py
python test_security.py

# Ручное тестирование через curl
# См. раздел "Команды безопасности" выше
```

### Проверка логов

```bash
# Просмотр логов в реальном времени (Linux/Mac)
tail -f logs/app.log

# Просмотр последних 50 строк (Windows PowerShell)
Get-Content logs/app.log -Tail 50

# Поиск ошибок в логах
grep ERROR logs/app.log
```

---

## 🛠️ Разработка

### Работа с Git

```bash
# Проверить статус
git status

# Добавить изменения
git add .

# Коммит с сообщением
git commit -m "Описание изменений"

# Не забудьте добавить .env в .gitignore!
# Проверьте .gitignore перед коммитом
```

### Очистка проекта

```bash
# Удалить кэш Python
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Удалить виртуальное окружение (если нужно пересоздать)
rm -rf venv  # Linux/Mac
rmdir /s venv  # Windows

# Очистить логи (если нужно)
> logs/app.log  # Linux/Mac
type nul > logs/app.log  # Windows
```

### Просмотр структуры базы данных

```bash
# Подключиться к PostgreSQL (имя БД из DATABASE_URL, обычно school_grades)
psql -U user -d school_grades

# В psql:
\dt                        # Список таблиц
\d users                   # Схема таблицы users
SELECT * FROM "user";      # Показать всех пользователей (таблица user в кавычках)
\q                         # Выйти
```

---

## 📦 Управление зависимостями

### Обновление requirements.txt

```bash
# Заморозить текущие версии пакетов
pip freeze > requirements.txt

# Проверить устаревшие пакеты
pip list --outdated

# Обновить конкретный пакет
pip install --upgrade package_name

# Обновить все пакеты
pip install --upgrade -r requirements.txt
```

### Создание backup requirements.txt

```bash
# Сохранить текущую версию перед обновлением
cp requirements.txt requirements.txt.backup
```

---

## 🌐 Production развертывание

### Подготовка к production

```bash
# 1. Установите в .env:
# FLASK_DEBUG=False
# SESSION_COOKIE_SECURE=True
# SECRET_KEY=<новый-сгенерированный-ключ>

# 2. Проверьте зависимости
safety check
pip-audit --rate-limit 20

# 3. Создайте backup базы данных (PostgreSQL)
pg_dump -U user school_grades > backup_$(date +%Y%m%d).sql

# 4. Примените миграции
python -m flask db upgrade
```

### Использование Gunicorn

```bash
# Установить Gunicorn
pip install gunicorn

# Запуск с 4 воркерами
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Запуск с логированием
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - app:app
```

### Использование systemd (Linux)

```bash
# Создать systemd service файл
sudo nano /etc/systemd/system/school-app.service

# Запустить сервис
sudo systemctl start school-app
sudo systemctl enable school-app  # Автозапуск при загрузке

# Проверить статус
sudo systemctl status school-app

# Просмотр логов
sudo journalctl -u school-app -f
```

---

## 🔍 Диагностика

### Проверка установки

```bash
# Проверить версию Python
python --version

# Проверить установленные пакеты
pip list | grep -i flask

# Проверить переменные окружения
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('SECRET_KEY'))"
```

### Проверка портов

```bash
# Проверить, занят ли порт 5000
netstat -ano | findstr :5000  # Windows
lsof -i :5000                  # Linux/Mac

# Изменить порт в app.py
# app.run(debug=debug_mode, host='0.0.0.0', port=8080)
```

---

## 📚 Полезные команды для разработки

### Форматирование кода

```bash
# Установить black (форматтер)
pip install black

# Форматировать код
black app.py forms.py schemas.py

# Проверка без изменения
black --check app.py
```

### Проверка кода

```bash
# Установить flake8 (линтер)
pip install flake8

# Проверить код
flake8 app.py

# Проверка с игнорированием некоторых правил
flake8 --ignore=E501,W503 app.py
```

---

## 💾 Backup и восстановление (PostgreSQL)

### Backup базы данных

```bash
# Дамп в файл (подставьте пользователя и имя БД из DATABASE_URL)
pg_dump -U user school_grades > backup_$(date +%Y%m%d_%H%M%S).sql

# Сжатый дамп
pg_dump -U user -Fc school_grades > backup.dump
```

### Восстановление из backup

```bash
# Восстановить из SQL-дампера
psql -U user -d school_grades < backup_YYYYMMDD.sql

# Из custom формата (-Fc)
pg_restore -U user -d school_grades backup.dump
```

---

**💡 Совет**: Добавьте наиболее часто используемые команды в ваш `.bashrc` или `.zshrc` для быстрого доступа:

```bash
# Пример алиасов
alias flask-migrate='python -m flask db migrate -m'
alias flask-upgrade='python -m flask db upgrade'
alias flask-downgrade='python -m flask db downgrade'
alias flask-current='python -m flask db current'
alias flask-history='python -m flask db history'
```

