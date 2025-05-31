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

        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDashboardData();
            });
        }

        // Tab change events
        const tabs = document.querySelectorAll('#dashboardTabs button[data-bs-toggle="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                const tabId = e.target.getAttribute('data-bs-target').replace('#', '');
                this.handleTabChange(tabId);
            });
        });
    }

    setDefaultDates() {
        const today = new Date();
        const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
        
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        
        if (startDate && endDate) {
            startDate.value = weekAgo.toISOString().split('T')[0];
            endDate.value = today.toISOString().split('T')[0];
            
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
                throw new Error('Failed to load dashboard data');
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
        const tableBody = document.getElementById('activeClientsTable');
        if (!tableBody || !clients) return;

        tableBody.innerHTML = '';

        // Update client statistics
        const uniqueCount = document.getElementById('uniqueClientsCount');
        const totalMessages = document.getElementById('totalClientMessages');
        const avgResponse = document.getElementById('avgClientResponseTime');

        if (uniqueCount) uniqueCount.textContent = clients.length;
        if (totalMessages) {
            const total = clients.reduce((sum, client) => sum + client.message_count, 0);
            totalMessages.textContent = total;
        }

        // Populate table
        clients.slice(0, 10).forEach(client => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.escapeHtml(client.name)}</td>
                <td>${client.message_count}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
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
                // Clients table is already populated
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