// Enhanced Dashboard with Filters
class FilteredDashboard {
    constructor() {
        this.adminToken = null;
        this.currentFilters = {
            chat_id: '',
            employee_id: '',
            start_date: '',
            end_date: ''
        };
        this.charts = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFilterOptions();
        this.setDefaultDates();
        this.loadDashboardData();
    }

    setupEventListeners() {
        // Filters form submission
        const filtersForm = document.getElementById('filtersForm');
        if (filtersForm) {
            filtersForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.applyFilters();
            });
        }

        // Tab change events - using your custom tab system
        const tabItems = document.querySelectorAll('.tab-item');
        tabItems.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remove active class from all tabs
                tabItems.forEach(t => t.classList.remove('active'));
                
                // Add active class to clicked tab
                tab.classList.add('active');
                
                // Hide all tab panes
                const tabPanes = document.querySelectorAll('.tab-pane');
                tabPanes.forEach(pane => pane.classList.remove('active'));
                
                // Show corresponding tab pane
                const targetTab = tab.getAttribute('data-tab');
                const targetPane = document.getElementById(targetTab);
                if (targetPane) {
                    targetPane.classList.add('active');
                    this.handleTabChange(targetTab);
                }
            });
        });
    }

    setDefaultDates() {
        // Get current date in Moscow timezone (UTC+3)
        const moscowTime = new Date(new Date().getTime() + (3 * 60 * 60 * 1000));
        const weekAgo = new Date(moscowTime.getTime() - 7 * 24 * 60 * 60 * 1000);
        
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        
        if (startDate && endDate) {
            // Format dates as YYYY-MM-DD in Moscow timezone
            startDate.value = weekAgo.toISOString().split('T')[0];
            endDate.value = moscowTime.toISOString().split('T')[0];
            
            this.currentFilters.start_date = startDate.value;
            this.currentFilters.end_date = endDate.value;
        }
    }

    async loadFilterOptions() {
        try {
            const response = await fetch('/api/filter-options', {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) {
                throw new Error('Failed to load filter options');
            }
            
            const data = await response.json();
            this.populateFilterOptions(data);
            
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    }

    populateFilterOptions(data) {
        // Populate chat filter
        const chatFilter = document.getElementById('chatFilter');
        if (chatFilter && data.chats) {
            chatFilter.innerHTML = '<option value="">Все чаты</option>';
            data.chats.forEach(chat => {
                const option = document.createElement('option');
                option.value = chat.id;
                option.textContent = chat.title;
                chatFilter.appendChild(option);
            });
        }

        // Populate employee filter
        const employeeFilter = document.getElementById('employeeFilter');
        if (employeeFilter && data.employees) {
            employeeFilter.innerHTML = '<option value="">Все сотрудники</option>';
            data.employees.forEach(employee => {
                const option = document.createElement('option');
                option.value = employee.id;
                option.textContent = employee.name;
                employeeFilter.appendChild(option);
            });
        }
    }

    applyFilters() {
        // Get form values
        this.currentFilters.chat_id = document.getElementById('chatFilter').value;
        this.currentFilters.employee_id = document.getElementById('employeeFilter').value;
        this.currentFilters.start_date = document.getElementById('startDate').value;
        this.currentFilters.end_date = document.getElementById('endDate').value;

        // Update period display
        this.updatePeriodDisplay();

        // Reload data with filters
        this.loadDashboardData();
    }

    updatePeriodDisplay() {
        const periodElement = document.getElementById('currentPeriod');
        if (periodElement && this.currentFilters.start_date && this.currentFilters.end_date) {
            periodElement.textContent = `Период: ${this.currentFilters.start_date} - ${this.currentFilters.end_date}`;
        }
    }

    async loadDashboardData() {
        try {
            // Build query string
            const params = new URLSearchParams();
            Object.keys(this.currentFilters).forEach(key => {
                if (this.currentFilters[key]) {
                    params.append(key, this.currentFilters[key]);
                }
            });

            const response = await fetch(`/api/filtered-dashboard-data?${params}`, {
                headers: this.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error('Ошибка загрузки данных');
            }

            const data = await response.json();
            this.updateDashboard(data);
            this.updateLastUpdated();

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('Ошибка загрузки данных: ' + error.message);
        }
    }

    updateDashboard(data) {
        // Update general statistics
        this.updateGeneralStats(data.general_stats);
        
        // Update employees tab
        this.updateEmployeesTab(data.employees);
        
        // Update clients tab
        this.updateClientsTab(data.clients);
        
        // Create charts based on current tab
        const activeTab = document.querySelector('#dashboardTabs .nav-link.active');
        if (activeTab) {
            const tabId = activeTab.getAttribute('data-bs-target').replace('#', '');
            this.handleTabChange(tabId);
        }
    }

    updateGeneralStats(stats) {
        // Update statistics cards
        const elements = {
            'totalMessagesStats': stats.total_messages,
            'totalSymbolsStats': stats.total_symbols,
            'teamMessagesStats': stats.team_messages,
            'clientMessagesStats': stats.client_messages,
            'avgResponseStats': `${stats.avg_response_time_minutes} мин`,
            'maxResponseStats': `${stats.max_response_time_minutes} мин`
        };

        Object.keys(elements).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = elements[id];
            }
        });

        // Update percentages
        const teamPercent = document.getElementById('teamMessagesPercent');
        if (teamPercent) {
            teamPercent.textContent = `${stats.team_percentage}% от общего числа`;
        }

        const clientPercent = document.getElementById('clientMessagesPercent');
        if (clientPercent) {
            clientPercent.textContent = `${stats.client_percentage}% от общего числа`;
        }
    }

    updateEmployeesTab(employees) {
        // Create employee activity chart
        if (employees && employees.length > 0) {
            this.createEmployeeChart(employees);
        }
    }

    updateClientsTab(clients) {
        if (!clients || !Array.isArray(clients)) {
            clients = [];
        }

        // Update client statistics
        this.updateClientStats(clients);
        
        // Create charts
        this.createClientCharts(clients);
        
        // Update client cards and table
        this.updateClientViews(clients);
    }

    updateClientStats(clients) {
        const totalClients = clients.length;
        const totalMessages = clients.reduce((sum, client) => sum + client.message_count, 0);
        const totalCharacters = clients.reduce((sum, client) => sum + (client.character_count || 0), 0);
        const avgMessages = totalClients > 0 ? Math.round(totalMessages / totalClients) : 0;

        // Update stat cards
        const stats = {
            'totalActiveClients': totalClients,
            'totalClientMessages': totalMessages,
            'avgMessagesPerClient': avgMessages,
            'totalClientCharacters': this.formatNumber(totalCharacters)
        };

        Object.keys(stats).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = stats[id];
            }
        });
    }

    createClientCharts(clients) {
        if (!clients.length) return;

        // Sort clients by message count for better visualization
        const sortedClients = [...clients].sort((a, b) => b.message_count - a.message_count);
        const topClients = sortedClients.slice(0, 10); // Show top 10 clients

        this.createClientActivityChart(topClients);
        this.createClientDistributionChart(topClients);
    }

    createClientActivityChart(clients) {
        const chartDiv = document.getElementById('clientActivityChart');
        if (!chartDiv || !clients.length) return;

        const trace = {
            x: clients.map(client => this.truncateName(client.name, 15)),
            y: clients.map(client => client.message_count),
            type: 'bar',
            name: 'Сообщения',
            marker: {
                color: clients.map((_, index) => {
                    const colors = ['#4361ee', '#3f37c9', '#4cc9f0', '#7209b7', '#560bad'];
                    return colors[index % colors.length];
                })
            },
            text: clients.map(client => `${client.message_count} сообщений<br>${client.character_count || 0} символов`),
            textposition: 'auto',
            hovertemplate: '<b>%{x}</b><br>Сообщений: %{y}<br>Символов: %{customdata}<extra></extra>',
            customdata: clients.map(client => client.character_count || 0)
        };

        const layout = {
            title: {
                text: 'Топ-10 наиболее активных клиентов',
                font: { size: 16, color: '#333' }
            },
            xaxis: { 
                title: 'Клиенты',
                tickangle: -45
            },
            yaxis: { title: 'Количество сообщений' },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#333' },
            margin: { l: 60, r: 30, t: 60, b: 100 }
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(chartDiv, [trace], layout, config);
        this.charts.clientActivityChart = chartDiv;
    }

    createClientDistributionChart(clients) {
        const chartDiv = document.getElementById('clientDistributionChart');
        if (!chartDiv || !clients.length) return;

        const totalMessages = clients.reduce((sum, client) => sum + client.message_count, 0);
        const topClients = clients.slice(0, 5); // Top 5 for pie chart
        const othersCount = clients.slice(5).reduce((sum, client) => sum + client.message_count, 0);

        const labels = topClients.map(client => this.truncateName(client.name, 12));
        const values = topClients.map(client => client.message_count);

        if (othersCount > 0) {
            labels.push('Остальные');
            values.push(othersCount);
        }

        const trace = {
            labels: labels,
            values: values,
            type: 'pie',
            hole: 0.4,
            marker: {
                colors: ['#4361ee', '#3f37c9', '#4cc9f0', '#7209b7', '#560bad', '#a663cc']
            },
            textinfo: 'label+percent',
            textposition: 'auto',
            hovertemplate: '<b>%{label}</b><br>Сообщений: %{value}<br>Доля: %{percent}<extra></extra>'
        };

        const layout = {
            title: {
                text: 'Распределение активности',
                font: { size: 16, color: '#333' }
            },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#333' },
            margin: { l: 20, r: 20, t: 60, b: 20 },
            showlegend: false
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(chartDiv, [trace], layout, config);
        this.charts.clientDistributionChart = chartDiv;
    }

    updateClientViews(clients) {
        this.updateClientCards(clients);
        this.updateClientTable(clients);
    }

    updateClientCards(clients) {
        const cardsContainer = document.getElementById('clientCardsView');
        if (!cardsContainer) return;

        cardsContainer.innerHTML = '';

        if (!clients.length) {
            cardsContainer.innerHTML = '<div class="text-center text-muted py-4">Нет данных о клиентах за выбранный период</div>';
            return;
        }

        const totalMessages = clients.reduce((sum, client) => sum + client.message_count, 0);

        clients.forEach(client => {
            const avgLength = client.character_count > 0 && client.message_count > 0 
                ? Math.round(client.character_count / client.message_count) 
                : 0;
            
            const activityPercent = totalMessages > 0 ? (client.message_count / totalMessages * 100) : 0;
            const activityLevel = this.getActivityLevel(client.message_count);
            const intensityPercent = this.calculateIntensity(client.message_count, clients);

            const card = document.createElement('div');
            card.className = 'client-card';
            card.innerHTML = `
                <div class="client-card-header">
                    <h4 class="client-name">
                        ${this.escapeHtml(client.name)}
                        <span class="activity-indicator ${activityLevel.class}"></span>
                    </h4>
                </div>
                <div class="client-card-body">
                    <div class="client-stats">
                        <div class="client-stat-item">
                            <div class="client-stat-value">${client.message_count}</div>
                            <div class="client-stat-label">Сообщений</div>
                        </div>
                        <div class="client-stat-item">
                            <div class="client-stat-value">${this.formatNumber(client.character_count || 0)}</div>
                            <div class="client-stat-label">Символов</div>
                        </div>
                    </div>
                    <div class="client-metrics">
                        <div class="client-metric">
                            <div class="client-metric-value">${avgLength}</div>
                            <div class="client-metric-label">Средняя длина</div>
                        </div>
                        <div class="client-metric">
                            <div class="client-metric-value">${activityPercent.toFixed(1)}%</div>
                            <div class="client-metric-label">Доля активности</div>
                        </div>
                    </div>
                    <div class="intensity-bar ${activityLevel.class}">
                        <div class="intensity-fill" style="width: ${intensityPercent}%"></div>
                    </div>
                </div>
            `;
            cardsContainer.appendChild(card);
        });
    }

    updateClientTable(clients) {
        const tableBody = document.getElementById('clientsTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        if (!clients.length) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="6" class="text-center text-muted py-4">Нет данных о клиентах за выбранный период</td>';
            tableBody.appendChild(row);
            return;
        }

        const totalMessages = clients.reduce((sum, client) => sum + client.message_count, 0);

        clients.forEach(client => {
            const avgLength = client.character_count > 0 && client.message_count > 0 
                ? Math.round(client.character_count / client.message_count) 
                : 0;
            
            const activityPercent = totalMessages > 0 ? (client.message_count / totalMessages * 100) : 0;
            const activityLevel = this.getActivityLevel(client.message_count);
            const intensityPercent = this.calculateIntensity(client.message_count, clients);

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    ${this.escapeHtml(client.name)}
                    <span class="activity-indicator ${activityLevel.class}"></span>
                </td>
                <td>${client.message_count}</td>
                <td>${this.formatNumber(client.character_count || 0)}</td>
                <td>${avgLength}</td>
                <td>${activityPercent.toFixed(1)}%</td>
                <td>
                    <div class="intensity-bar ${activityLevel.class}">
                        <div class="intensity-fill" style="width: ${intensityPercent}%"></div>
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    createEmployeeChart(employees) {
        const chartDiv = document.getElementById('employeeActivityChart');
        if (!chartDiv || !employees.length) return;

        const trace = {
            x: employees.map(emp => emp.name),
            y: employees.map(emp => emp.message_count),
            type: 'bar',
            name: 'Сообщения',
            marker: {
                color: 'rgba(54, 162, 235, 0.8)'
            }
        };

        const layout = {
            title: 'Активность сотрудников',
            xaxis: { title: 'Сотрудники' },
            yaxis: { title: 'Количество сообщений' },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#ffffff' }
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(chartDiv, [trace], layout, config);
        this.charts.employeeChart = chartDiv;
    }

    handleTabChange(tabId) {
        // Handle specific tab activations
        switch (tabId) {
            case 'employees':
                // Employee chart is already created
                break;
            case 'clients':
                // Clients visualizations are already created
                break;
            case 'activity':
                // You can add activity chart here
                break;
            case 'sentiment':
                // You can add sentiment chart here
                break;
            case 'communications':
                // You can add communications chart here
                break;
        }
    }

    // Helper functions for client visualization
    getActivityLevel(messageCount) {
        if (messageCount >= 50) {
            return { class: 'activity-high', level: 'Высокая' };
        } else if (messageCount >= 20) {
            return { class: 'activity-medium', level: 'Средняя' };
        } else {
            return { class: 'activity-low', level: 'Низкая' };
        }
    }

    calculateIntensity(messageCount, allClients) {
        if (!allClients.length) return 0;
        const maxMessages = Math.max(...allClients.map(c => c.message_count));
        return maxMessages > 0 ? (messageCount / maxMessages * 100) : 0;
    }

    truncateName(name, maxLength) {
        if (!name) return 'Unknown';
        return name.length > maxLength ? name.substring(0, maxLength) + '...' : name;
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    // Client chart controls
    toggleClientChartType(type) {
        // Update button states
        const buttons = document.querySelectorAll('.chart-controls .btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        // Get current clients data and recreate chart
        // This would be implemented when we have the data
        console.log('Toggle chart type to:', type);
    }

    toggleClientView(viewType) {
        // Update button states
        const buttons = document.querySelectorAll('.client-view-controls .btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        // Show/hide views
        const cardsView = document.getElementById('clientCardsView');
        const tableView = document.getElementById('clientTableView');

        if (viewType === 'cards') {
            cardsView.style.display = 'block';
            tableView.style.display = 'none';
        } else {
            cardsView.style.display = 'none';
            tableView.style.display = 'block';
        }
    }

    getAuthHeaders() {
        const token = this.getAdminToken();
        return token ? { 'X-Admin-Token': token } : {};
    }

    getAdminToken() {
        // Try to get from global variable first
        if (window.adminToken) {
            return window.adminToken;
        }
        
        // Fallback to localStorage
        return localStorage.getItem('adminToken');
    }

    updateLastUpdated() {
        const element = document.getElementById('lastUpdated');
        if (element) {
            element.textContent = new Date().toLocaleString('ru-RU');
        }
    }

    showError(message) {
        // You can implement a toast notification or alert here
        console.error(message);
        alert(message);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Set admin token from template if available
    if (typeof adminToken !== 'undefined') {
        window.adminToken = adminToken;
    }
    
    // Initialize dashboard
    new FilteredDashboard();
});