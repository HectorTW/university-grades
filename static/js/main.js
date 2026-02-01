// Основные JavaScript функции

// Функция для отправки оценок
function submitGrades() {
    const subject = document.getElementById('subject').value;
    const grades = [];
    
    // Собираем данные по всем студентам
    document.querySelectorAll('.student-row').forEach(row => {
        const studentId = row.dataset.studentId;
        const grade = row.querySelector('.grade-input').value;
        const diligence = row.querySelector('.diligence-input').value;
        const knowledge = row.querySelector('.knowledge-input').value;
        const comment = row.querySelector('.comment-input').value;
        
        if (grade && diligence && knowledge) {
            grades.push({
                student_id: studentId,
                grade: parseInt(grade),
                diligence: parseInt(diligence),
                knowledge: parseInt(knowledge),
                comment: comment
            });
        }
    });
    
    if (grades.length === 0) {
        alert('Пожалуйста, заполните хотя бы одну оценку');
        return;
    }
    
    if (!subject) {
        alert('Пожалуйста, укажите предмет');
        return;
    }
    
    // Отправляем данные на сервер (с CSRF-токеном)
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const headers = {
        'Content-Type': 'application/json',
    };
    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }

    fetch('/teacher/submit_grades', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
            subject: subject,
            grades: grades
        }),
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().catch(() => { throw new Error('Ошибка сервера'); });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('Оценки успешно сохранены!');
            // Очищаем форму
            document.querySelectorAll('.grade-input, .diligence-input, .knowledge-input, .comment-input').forEach(input => {
                input.value = '';
            });
            document.getElementById('subject').value = '';
        } else {
            alert('Ошибка при сохранении оценок: ' + (data.message || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка при отправке данных');
    });
}

// Функция для валидации оценок
function validateGrade(input) {
    const value = parseInt(input.value);
    if (value < 1 || value > 5) {
        input.value = '';
        alert('Оценка должна быть от 1 до 5');
    }
}

// Функция для подсчета среднего балла
function calculateAverage(studentId) {
    const row = document.querySelector(`[data-student-id="${studentId}"]`);
    const grade = parseInt(row.querySelector('.grade-input').value) || 0;
    const diligence = parseInt(row.querySelector('.diligence-input').value) || 0;
    const knowledge = parseInt(row.querySelector('.knowledge-input').value) || 0;
    
    if (grade && diligence && knowledge) {
        const average = ((grade + diligence + knowledge) / 3).toFixed(1);
        const averageCell = row.querySelector('.average-cell');
        averageCell.textContent = average;
        averageCell.className = 'average-cell text-center fw-bold';
        
        // Цветовая индикация
        if (average >= 4.5) {
            averageCell.classList.add('text-success');
        } else if (average >= 3.5) {
            averageCell.classList.add('text-warning');
        } else {
            averageCell.classList.add('text-danger');
        }
    } else {
        const averageCell = row.querySelector('.average-cell');
        averageCell.textContent = '-';
        averageCell.className = 'average-cell text-center';
    }
}

// Добавляем обработчики событий после загрузки страницы
document.addEventListener('DOMContentLoaded', function() {
    // Обработчики для полей оценок
    document.querySelectorAll('.grade-input, .diligence-input, .knowledge-input').forEach(input => {
        input.addEventListener('blur', function() {
            validateGrade(this);
            const studentId = this.closest('.student-row').dataset.studentId;
            calculateAverage(studentId);
        });
    });
    
    // Обработчик для кнопки отправки
    const submitBtn = document.getElementById('submit-grades');
    if (submitBtn) {
        submitBtn.addEventListener('click', submitGrades);
    }
    
    // Анимация появления карточек
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
});

// Функция для подтверждения удаления
function confirmDelete(message) {
    return confirm(message || 'Вы уверены, что хотите удалить этот элемент?');
}

// Функция для показа/скрытия пароля
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const icon = document.querySelector(`[onclick="togglePassword('${inputId}')"] i`);
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}
