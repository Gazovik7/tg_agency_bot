document.addEventListener('DOMContentLoaded', function() {
    // Инициализация графиков
    initializeCharts();
    
    // Обработчики событий для фильтров
    setupFilters();
    
    // Обработчики событий для табов
    setupTabs();
});

function initializeCharts() {
    // Получаем данные для графиков
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.charts) {
                // График производительности
                if (data.charts.staff_performance) {
                    plotChart('staff-performance-chart', data.charts.staff_performance);
                }
                
                // Радарный график
                if (data.charts.staff_radar) {
                    plotChart('staff-radar-chart', data.charts.staff_radar);
                }
                
                // График недельной активности
                if (data.charts.staff_weekly) {
                    plotChart('staff-weekly-chart', data.charts.staff_weekly);
                }
            }
        })
        .catch(error => console.error('Ошибка при загрузке данных:', error));
}

function plotChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data) return;
    
    const layout = {
        margin: { t: 30, r: 30, b: 30, l: 30 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
            family: 'Inter, sans-serif',
            size: 12,
            color: '#6c757d'
        }
    };
    
    Plotly.newPlot(containerId, data, layout);
}

function setupFilters() {
    const chatSelect = document.getElementById('chat-filter');
    const staffSelect = document.getElementById('staff-filter');
    const dateRange = document.getElementById('date-range');
    
    if (chatSelect) {
        chatSelect.addEventListener('change', updateDashboard);
    }
    
    if (staffSelect) {
        staffSelect.addEventListener('change', updateDashboard);
    }
    
    if (dateRange) {
        dateRange.addEventListener('change', updateDashboard);
    }
}

function setupTabs() {
    const tabItems = document.querySelectorAll('.nav-link');
    
    tabItems.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Удаляем активный класс у всех табов
            tabItems.forEach(t => t.classList.remove('active'));
            
            // Добавляем активный класс текущему табу
            this.classList.add('active');
            
            // Показываем соответствующий контент
            const targetId = this.getAttribute('href').substring(1);
            const tabContents = document.querySelectorAll('.tab-content');
            
            tabContents.forEach(content => {
                content.style.display = content.id === targetId ? 'block' : 'none';
            });
        });
    });
}

function updateDashboard() {
    const chatFilter = document.getElementById('chat-filter').value;
    const staffFilter = document.getElementById('staff-filter').value;
    const dateRange = document.getElementById('date-range').value;
    
    // Обновляем статистику
    fetch(`/api/stats?chat=${chatFilter}&staff=${staffFilter}&date_range=${dateRange}`)
        .then(response => response.json())
        .then(data => {
            updateStatistics(data);
            if (data.charts) {
                updateCharts(data.charts);
            }
        })
        .catch(error => console.error('Ошибка при обновлении данных:', error));
}

function updateStatistics(data) {
    // Обновляем значения статистики
    const stats = {
        'total-messages': data.total_messages || 0,
        'avg-length': data.avg_length || 0,
        'avg-sentiment': data.avg_sentiment || 0,
        'team-messages': data.team_messages || 0,
        'client-messages': data.client_messages || 0
    };
    
    Object.entries(stats).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

function updateCharts(charts) {
    if (charts.staff_performance) {
        plotChart('staff-performance-chart', charts.staff_performance);
    }
    if (charts.staff_radar) {
        plotChart('staff-radar-chart', charts.staff_radar);
    }
    if (charts.staff_weekly) {
        plotChart('staff-weekly-chart', charts.staff_weekly);
    }
} 