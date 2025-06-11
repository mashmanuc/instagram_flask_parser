/**
 * Головний JavaScript файл для Instagram Scraper
 */

document.addEventListener('DOMContentLoaded', function() {
    // Ініціалізація підказок Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Додаємо обробник подій для заміни зображень, які не завантажилися
    const handleImageErrors = function() {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            img.addEventListener('error', function() {
                // SVG плейсхолдер
                const svgPlaceholder = `
                <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="225" viewBox="0 0 400 225">
                    <rect width="400" height="225" fill="#f8f9fa" />
                    <text x="50%" y="50%" font-family="Arial" font-size="18" text-anchor="middle" fill="#6c757d">Немає зображення</text>
                    <text x="50%" y="65%" font-family="Arial" font-size="14" text-anchor="middle" fill="#6c757d">Джерело недоступне</text>
                </svg>
                `;
                
                // Кодуємо SVG для використання в src
                const encodedSvg = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svgPlaceholder);
                this.src = encodedSvg;
            });
        });
    };
    
    // Запускаємо обробник при завантаженні сторінки
    handleImageErrors();

    // Функція для оновлення статусу скрапінгу
    function updateScrapingStatus() {
        const statusBadge = document.getElementById('status-badge');
        const statusMessage = document.getElementById('status-message');
        const progressBar = document.getElementById('progress-bar');
        
        if (!statusBadge || !statusMessage) {
            return;
        }
        
        fetch('/status')
            .then(response => response.json())
            .then(data => {
                // Оновлення тексту статусу
                let statusText = 'Очікування';
                let badgeClass = 'bg-secondary';
                let alertClass = 'alert-info';
                
                if (data.status === 'running') {
                    statusText = 'Виконується';
                    badgeClass = 'bg-warning';
                    alertClass = 'alert-warning';
                } else if (data.status === 'completed') {
                    statusText = 'Завершено';
                    badgeClass = 'bg-success';
                    alertClass = 'alert-success';
                } else if (data.status === 'error') {
                    statusText = 'Помилка';
                    badgeClass = 'bg-danger';
                    alertClass = 'alert-danger';
                }
                
                // Оновлення класів та тексту елементів
                statusBadge.textContent = statusText;
                statusBadge.className = 'badge ' + badgeClass;
                
                statusMessage.textContent = data.message;
                statusMessage.className = 'alert ' + alertClass;
                
                // Оновлення прогрес-бару, якщо він існує
                if (progressBar) {
                    progressBar.style.width = data.progress + '%';
                }
                
                // Оновлення логів, якщо контейнер існує
                const logContainer = document.getElementById('log-content');
                if (logContainer) {
                    // Отримуємо логи з сервера
                    fetch('/get_logs')
                        .then(response => response.json())
                        .then(logData => {
                            if (logData.logs && logData.logs.length > 0) {
                                // Форматуємо логи з кольорами
                                const formattedLogs = logData.logs.map(log => {
                                    let logClass = 'text-light';
                                    if (log.includes('INFO')) logClass = 'text-info';
                                    if (log.includes('WARNING')) logClass = 'text-warning';
                                    if (log.includes('ERROR')) logClass = 'text-danger';
                                    if (log.includes('дублікат')) logClass = 'text-warning';
                                    
                                    return `<div class="${logClass}">${log}</div>`;
                                }).join('');
                                
                                logContainer.innerHTML = formattedLogs;
                                
                                // Прокручуємо до останнього запису
                                const logContainerParent = document.getElementById('log-container');
                                if (logContainerParent) {
                                    logContainerParent.scrollTop = logContainerParent.scrollHeight;
                                }
                            }
                        })
                        .catch(error => console.error('Помилка при отриманні логів:', error));
                }
                
                // Оновлення лічильника дублікатів
                const duplicatesCount = document.getElementById('duplicates-count');
                if (duplicatesCount && data.duplicates_skipped !== undefined) {
                    duplicatesCount.textContent = data.duplicates_skipped;
                }
                
                // Якщо процес завершився, перезавантажуємо сторінку
                if (data.is_running === false && data.status !== 'idle') {
                    setTimeout(() => {
                        location.reload();
                    }, 3000);
                }
                
                // Зберігаємо поточний статус
                statusBadge.dataset.running = (data.status === 'running').toString();
                
                // Продовжуємо оновлювати, якщо процес все ще виконується
                if (data.is_running) {
                    setTimeout(updateScrapingStatus, 2000);
                }
            })
            .catch(error => {
                console.error('Помилка при оновленні статусу:', error);
                setTimeout(updateScrapingStatus, 5000);
            });
    }
    
    // Оновлення статусу кожні 3 секунди, якщо ми на головній сторінці
    if (window.location.pathname === '/' || window.location.pathname === '/index') {
        const statusBadge = document.getElementById('status-badge');
        if (statusBadge && statusBadge.textContent.trim() === 'Виконується') {
            setInterval(updateScrapingStatus, 3000);
        }
    }
    
    // Обробка помилок завантаження зображень
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        img.addEventListener('error', function() {
            // Використовуємо вбудоване зображення замість файлу
            this.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22300%22%20height%3D%22200%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20300%20200%22%20preserveAspectRatio%3D%22none%22%3E%3Cdefs%3E%3Cstyle%20type%3D%22text%2Fcss%22%3E%23holder_189e85d00a8%20text%20%7B%20fill%3A%23AAAAAA%3Bfont-weight%3Abold%3Bfont-family%3AArial%2C%20Helvetica%2C%20Open%20Sans%2C%20sans-serif%2C%20monospace%3Bfont-size%3A15pt%20%7D%20%3C%2Fstyle%3E%3C%2Fdefs%3E%3Cg%20id%3D%22holder_189e85d00a8%22%3E%3Crect%20width%3D%22300%22%20height%3D%22200%22%20fill%3D%22%23EEEEEE%22%3E%3C%2Frect%3E%3Cg%3E%3Ctext%20x%3D%22110.5%22%20y%3D%22107.1%22%3EНемає%20зображення%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E';
            this.alt = 'Зображення недоступне';
        });
    });
    
    // Анімація для карток
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('fade-in');
    });
    
    // Підтвердження видалення
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Ви впевнені, що хочете видалити цей запис?')) {
                e.preventDefault();
            }
        });
    });
    
    // Копіювання URL у буфер обміну
    const copyButtons = document.querySelectorAll('.copy-url-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            navigator.clipboard.writeText(url).then(() => {
                // Змінюємо текст кнопки на короткий час
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check"></i> Скопійовано';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });
    
    // Показати/сховати пароль
    const togglePasswordBtn = document.getElementById('toggle-password');
    if (togglePasswordBtn) {
        togglePasswordBtn.addEventListener('click', function() {
            const passwordInput = document.getElementById('instagram_password');
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                this.innerHTML = '<i class="bi bi-eye-slash"></i>';
            } else {
                passwordInput.type = 'password';
                this.innerHTML = '<i class="bi bi-eye"></i>';
            }
        });
    }
});
