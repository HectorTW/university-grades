// Основные JavaScript функции

document.addEventListener('DOMContentLoaded', function() {
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

function confirmDelete(message) {
    return confirm(message || 'Вы уверены, что хотите удалить этот элемент?');
}

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
