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

        // Add activity grouping change listener
        const activityGrouping = document.getElementById('activityGrouping');
        if (activityGrouping) {
            activityGrouping.addEventListener('change', () => {
                const activeTab = document.querySelector('.tab-item[data-tab="activity"]');
                if (activeTab && activeTab.classList.contains('active')) {
                    this.loadActivityData();
                }
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
            console.log('Loading dashboard data with filters:', this.currentFilters);
            console.log('Request URL:', `/api/filtered-dashboard-data?${params}`);
            console.log('Auth headers:', this.getAuthHeaders());
            console.log('Response status:', response.status);
            console.log('Received data:', data);
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
            'maxResponseStats': `${stats.max_response_time_minutes} мин`,
            'medianResponseStats': `${stats.median_response_time_minutes || 0} мин`
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
        const totalMessages = clients.reduce((sum, client) => sum + client.total_messages, 0);
        const totalCharacters = clients.reduce((sum, client) => sum + client.total_characters, 0);
        const totalClientMessages = clients.reduce((sum, client) => sum + client.client_messages, 0);
        const avgMessages = totalClients > 0 ? Math.round(totalMessages / totalClients) : 0;

        // Update stat cards
        const stats = {
            'totalActiveClients': totalClients,
            'totalClientMessages': totalClientMessages,
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

        // Sort clients by communication intensity
        const sortedClients = [...clients].sort((a, b) => b.communication_intensity - a.communication_intensity);
        const topClients = sortedClients.slice(0, 10); // Show top 10 clients

        this.createClientActivityChart(topClients);
        this.createClientDistributionChart(topClients);
    }

    createClientActivityChart(clients) {
        const chartDiv = document.getElementById('clientActivityChart');
        if (!chartDiv || !clients.length) return;

        // Create grouped bar chart showing team vs client messages
        const teamTrace = {
            x: clients.map(client => this.truncateName(client.name, 15)),
            y: clients.map(client => client.team_messages),
            type: 'bar',
            name: 'Наша команда',
            marker: { color: '#4361ee' },
            hovertemplate: '<b>%{x}</b><br>Сообщений от нашей команды: %{y}<br>Символов: %{customdata}<extra></extra>',
            customdata: clients.map(client => client.team_characters)
        };

        const clientTrace = {
            x: clients.map(client => this.truncateName(client.name, 15)),
            y: clients.map(client => client.client_messages),
            type: 'bar',
            name: 'Команда клиента',
            marker: { color: '#4cc9f0' },
            hovertemplate: '<b>%{x}</b><br>Сообщений от команды клиента: %{y}<br>Символов: %{customdata}<extra></extra>',
            customdata: clients.map(client => client.client_characters)
        };

        const layout = {
            title: {
                text: 'Объем коммуникаций с клиентами',
                font: { size: 16, color: '#333' }
            },
            xaxis: { 
                title: 'Клиенты',
                tickangle: -45
            },
            yaxis: { title: 'Количество сообщений' },
            barmode: 'group',
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#333' },
            margin: { l: 60, r: 30, t: 60, b: 100 },
            legend: {
                orientation: 'h',
                y: -0.2
            }
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(chartDiv, [teamTrace, clientTrace], layout, config);
        this.charts.clientActivityChart = chartDiv;
    }

    createClientDistributionChart(clients) {
        const chartDiv = document.getElementById('clientDistributionChart');
        if (!chartDiv || !clients.length) return;

        // Show overall team vs client communication distribution
        const totalTeamMessages = clients.reduce((sum, client) => sum + client.team_messages, 0);
        const totalClientMessages = clients.reduce((sum, client) => sum + client.client_messages, 0);

        const trace = {
            labels: ['Наша команда', 'Команды клиентов'],
            values: [totalTeamMessages, totalClientMessages],
            type: 'pie',
            hole: 0.4,
            marker: {
                colors: ['#4361ee', '#4cc9f0']
            },
            textinfo: 'label+percent+value',
            textposition: 'auto',
            hovertemplate: '<b>%{label}</b><br>Сообщений: %{value}<br>Доля: %{percent}<extra></extra>'
        };

        const layout = {
            title: {
                text: 'Соотношение активности команд',
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

        const totalMessages = clients.reduce((sum, client) => sum + client.total_messages, 0);

        clients.forEach(client => {
            const activityPercent = totalMessages > 0 ? (client.total_messages / totalMessages * 100) : 0;
            const activityLevel = this.getActivityLevel(client.total_messages);
            const intensityPercent = this.calculateIntensity(client.total_messages, clients);

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
                            <div class="client-stat-value" style="color: #4361ee">${client.team_messages}</div>
                            <div class="client-stat-label">Наша команда</div>
                        </div>
                        <div class="client-stat-item">
                            <div class="client-stat-value" style="color: #4cc9f0">${client.client_messages}</div>
                            <div class="client-stat-label">Команда клиента</div>
                        </div>
                    </div>
                    <div class="client-metrics">
                        <div class="client-metric">
                            <div class="client-metric-value">${this.formatNumber(client.team_characters)}</div>
                            <div class="client-metric-label">Символов от нас</div>
                        </div>
                        <div class="client-metric">
                            <div class="client-metric-value">${this.formatNumber(client.client_characters)}</div>
                            <div class="client-metric-label">Символов от клиента</div>
                        </div>
                        <div class="client-metric">
                            <div class="client-metric-value">${client.team_message_ratio}%</div>
                            <div class="client-metric-label">Наша доля</div>
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
            row.innerHTML = '<td colspan="7" class="text-center text-muted py-4">Нет данных о клиентах за выбранный период</td>';
            tableBody.appendChild(row);
            return;
        }

        const totalMessages = clients.reduce((sum, client) => sum + client.total_messages, 0);

        clients.forEach(client => {
            const activityPercent = totalMessages > 0 ? (client.total_messages / totalMessages * 100) : 0;
            const activityLevel = this.getActivityLevel(client.total_messages);
            const intensityPercent = this.calculateIntensity(client.total_messages, clients);

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    ${this.escapeHtml(client.name)}
                    <span class="activity-indicator ${activityLevel.class}"></span>
                </td>
                <td>
                    <span style="color: #4361ee; font-weight: 600;">${client.team_messages}</span> / 
                    <span style="color: #4cc9f0; font-weight: 600;">${client.client_messages}</span>
                </td>
                <td>
                    <span style="color: #4361ee;">${this.formatNumber(client.team_characters)}</span> / 
                    <span style="color: #4cc9f0;">${this.formatNumber(client.client_characters)}</span>
                </td>
                <td>${this.formatResponseTime(client.avg_response_time_minutes)}</td>
                <td>${this.formatResponseTime(client.max_response_time_minutes)}</td>
                <td>${this.formatResponseTime(client.median_response_time_minutes)}</td>
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
        console.log('Tab changed to:', tabId);
        // Handle specific tab activations
        switch (tabId) {
            case 'employees':
                // Employee chart is already created
                break;
            case 'clients':
                // Clients visualizations are already created
                break;
            case 'activity':
                console.log('Activity tab activated, preparing to load data...');
                // Load activity data when tab is activated
                setTimeout(() => {
                    console.log('Activity data load timeout triggered');
                    this.loadActivityData();
                }, 200); // Increased delay to ensure DOM is ready
                break;
            case 'sentiment':
                // Load sentiment data when tab is activated
                this.loadSentimentData();
                break;
            case 'communications':
                // Load communications data when tab is activated
                this.loadCommunicationsData();
                break;
        }
    }

    // Activity Tab Methods
    async loadActivityData() {
        try {
            // Check if activity grouping element exists
            const groupingElement = document.getElementById('activityGrouping');
            if (!groupingElement) {
                console.log('Activity grouping element not found, skipping activity data load');
                return;
            }

            // Check if we're actually on the activity tab
            const activityTab = document.querySelector('.tab-item[data-tab="activity"]');
            if (!activityTab || !activityTab.classList.contains('active')) {
                console.log('Not on activity tab, skipping data load');
                return;
            }

            const filters = this.getFilters();
            const grouping = groupingElement.value || 'day';
            
            console.log('Loading activity data with filters:', filters, 'grouping:', grouping);

            // Build URL parameters manually to avoid issues
            const params = new URLSearchParams();
            if (filters.start_date) params.append('start_date', filters.start_date);
            if (filters.end_date) params.append('end_date', filters.end_date);
            if (filters.chat_id) params.append('chat_id', filters.chat_id);
            if (filters.employee_id) params.append('employee_id', filters.employee_id);
            params.append('grouping', grouping);

            const url = `/api/activity-data?${params.toString()}`;
            console.log('Activity API URL:', url);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: this.getAuthHeaders()
            });
            
            console.log('Activity API response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API error response:', errorText);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            console.log('Activity data received:', data);
            
            this.updateActivityTab(data, grouping);
        } catch (error) {
            console.error('Error loading activity data:', error);
            console.error('Error stack:', error.stack);
            console.error('Error name:', error.name);
            console.error('Error message:', error.message);
            
            // Only show error if we're on the activity tab
            const activityTab = document.querySelector('.tab-item[data-tab="activity"]');
            if (activityTab && activityTab.classList.contains('active')) {
                this.showError('Ошибка загрузки данных активности');
            }
        }
    }

    updateActivityTab(data, grouping) {
        // Update key metrics
        this.updateActivityMetrics(data.metrics, grouping);
        
        // Create charts
        this.createActivityTimeSeries(data.timeSeries, grouping);
        this.createActivityHourHistogram(data.hourDistribution);
        this.createActivityHeatmaps(data.heatmaps);
    }

    updateActivityMetrics(metrics, grouping) {
        try {
            const periodLabels = {
                'day': 'в день',
                'week': 'в неделю', 
                'month': 'в месяц'
            };

            // Check if elements exist before updating
            const elements = [
                'activityTotalMessages',
                'activityAvgPerPeriod', 
                'activityAvgLabel',
                'activityPeakPeriod',
                'activityPeakCount',
                'activityPeakHour',
                'activityPeakHourCount'
            ];

            for (const elementId of elements) {
                const element = document.getElementById(elementId);
                if (!element) {
                    console.warn(`Element ${elementId} not found`);
                    return;
                }
            }

            document.getElementById('activityTotalMessages').textContent = metrics.totalMessages || 0;
            document.getElementById('activityAvgPerPeriod').textContent = metrics.avgPerPeriod || 0;
            document.getElementById('activityAvgLabel').textContent = `сообщений ${periodLabels[grouping]}`;
            document.getElementById('activityPeakPeriod').textContent = metrics.peakPeriod || '-';
            document.getElementById('activityPeakCount').textContent = `${metrics.peakCount || 0} сообщений`;
            document.getElementById('activityPeakHour').textContent = metrics.peakHour !== undefined ? `${metrics.peakHour}:00` : '-';
            document.getElementById('activityPeakHourCount').textContent = `${metrics.peakHourCount || 0} сообщений`;
        } catch (error) {
            console.error('Error updating activity metrics:', error);
        }
    }

    createActivityTimeSeries(data, grouping) {
        const traces = [
            {
                x: data.periods,
                y: data.clientMessages,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Сообщения клиентов',
                line: { color: '#4cc9f0', width: 3 },
                marker: { size: 6 }
            },
            {
                x: data.periods,
                y: data.teamMessages,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Сообщения команды',
                line: { color: '#4361ee', width: 3 },
                marker: { size: 6 }
            }
        ];

        const layout = {
            title: {
                text: `Динамика сообщений по ${grouping === 'day' ? 'дням' : grouping === 'week' ? 'неделям' : 'месяцам'}`,
                font: { size: 16, family: 'Inter, sans-serif' }
            },
            xaxis: {
                title: grouping === 'day' ? 'Дата' : grouping === 'week' ? 'Неделя' : 'Месяц',
                gridcolor: '#e1e5e9'
            },
            yaxis: {
                title: 'Количество сообщений',
                gridcolor: '#e1e5e9'
            },
            hovermode: 'x unified',
            showlegend: true,
            legend: { orientation: 'h', y: -0.2 },
            margin: { t: 60, r: 40, b: 60, l: 60 },
            paper_bgcolor: 'white',
            plot_bgcolor: 'white'
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot('activityTimeSeriesChart', traces, layout, config);
    }

    createActivityHourHistogram(data) {
        const traces = [
            {
                x: Array.from({length: 24}, (_, i) => i),
                y: data.clientMessages,
                type: 'bar',
                name: 'Клиенты',
                marker: { color: '#4cc9f0' }
            },
            {
                x: Array.from({length: 24}, (_, i) => i),
                y: data.teamMessages,
                type: 'bar',
                name: 'Команда',
                marker: { color: '#4361ee' }
            }
        ];

        const layout = {
            title: {
                text: 'Распределение сообщений по часам дня',
                font: { size: 16, family: 'Inter, sans-serif' }
            },
            xaxis: {
                title: 'Час дня',
                tickmode: 'array',
                tickvals: Array.from({length: 24}, (_, i) => i),
                ticktext: Array.from({length: 24}, (_, i) => `${i}:00`),
                gridcolor: '#e1e5e9'
            },
            yaxis: {
                title: 'Количество сообщений',
                gridcolor: '#e1e5e9'
            },
            barmode: 'stack',
            hovermode: 'x unified',
            showlegend: true,
            legend: { orientation: 'h', y: -0.2 },
            margin: { t: 60, r: 40, b: 60, l: 60 },
            paper_bgcolor: 'white',
            plot_bgcolor: 'white'
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot('activityHourHistogram', traces, layout, config);
    }

    createActivityHeatmaps(data) {
        const dayLabels = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];
        const hourLabels = Array.from({length: 24}, (_, i) => `${i}:00`);

        // Client heatmap
        const clientTrace = {
            z: data.client,
            type: 'heatmap',
            colorscale: [
                [0, '#f8f9fa'],
                [0.25, '#cce7ff'],
                [0.5, '#66c2ff'],
                [0.75, '#1a8cff'],
                [1, '#0066cc']
            ],
            showscale: true,
            hoverongaps: false,
            hovertemplate: '%{y}, %{x}<br>Сообщений: %{z}<extra></extra>'
        };

        const clientLayout = {
            title: {
                text: 'Активность клиентов',
                font: { size: 14, family: 'Inter, sans-serif' }
            },
            xaxis: {
                title: 'Час',
                tickmode: 'array',
                tickvals: Array.from({length: 24}, (_, i) => i),
                ticktext: hourLabels,
                side: 'bottom'
            },
            yaxis: {
                title: 'День недели',
                tickmode: 'array',
                tickvals: [0, 1, 2, 3, 4, 5, 6],
                ticktext: dayLabels,
                autorange: 'reversed'
            },
            margin: { t: 40, r: 60, b: 60, l: 100 },
            height: 300
        };

        // Team heatmap
        const teamTrace = {
            z: data.team,
            type: 'heatmap',
            colorscale: [
                [0, '#fff7ed'],
                [0.25, '#fed7aa'],
                [0.5, '#fb923c'],
                [0.75, '#ea580c'],
                [1, '#c2410c']
            ],
            showscale: true,
            hoverongaps: false,
            hovertemplate: '%{y}, %{x}<br>Сообщений: %{z}<extra></extra>'
        };

        const teamLayout = {
            title: {
                text: 'Активность команды',
                font: { size: 14, family: 'Inter, sans-serif' }
            },
            xaxis: {
                title: 'Час',
                tickmode: 'array',
                tickvals: Array.from({length: 24}, (_, i) => i),
                ticktext: hourLabels,
                side: 'bottom'
            },
            yaxis: {
                title: 'День недели',
                tickmode: 'array',
                tickvals: [0, 1, 2, 3, 4, 5, 6],
                ticktext: dayLabels,
                autorange: 'reversed'
            },
            margin: { t: 40, r: 60, b: 60, l: 100 },
            height: 300
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot('activityClientHeatmap', [clientTrace], clientLayout, config);
        Plotly.newPlot('activityTeamHeatmap', [teamTrace], teamLayout, config);
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
        const maxMessages = Math.max(...allClients.map(c => c.total_messages || c.message_count || 0));
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

    formatResponseTime(minutes) {
        if (!minutes || minutes === 0) {
            return '<span class="text-muted">—</span>';
        }
        
        let colorClass = 'text-success';
        if (minutes > 60) {
            colorClass = 'text-danger';
        } else if (minutes > 15) {
            colorClass = 'text-warning';
        }
        
        if (minutes >= 60) {
            const hours = Math.floor(minutes / 60);
            const remainingMinutes = Math.round(minutes % 60);
            return `<span class="${colorClass}">${hours}ч ${remainingMinutes}м</span>`;
        } else {
            return `<span class="${colorClass}">${Math.round(minutes)}м</span>`;
        }
    }

    // Sentiment Analysis Functions
    async loadSentimentData() {
        console.log('Loading sentiment data with filters:', this.currentFilters);
        
        const params = new URLSearchParams();
        Object.entries(this.currentFilters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });
        
        const url = `/api/sentiment-overview?${params.toString()}`;
        console.log('Request URL:', url);
        
        const authHeaders = this.getAuthHeaders();
        console.log('Auth headers:', authHeaders);
        
        try {
            const response = await fetch(url, { headers: authHeaders });
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received sentiment data:', data);
            
            this.updateSentimentDisplay(data);
        } catch (error) {
            console.error('Error loading sentiment data:', error);
            this.showError('Ошибка загрузки данных тональности');
        }
    }

    updateSentimentDisplay(data) {
        const summary = data.summary || {};
        
        // Update sentiment statistics
        document.getElementById('positiveCount').textContent = summary.positive || 0;
        document.getElementById('positivePercentage').textContent = `${summary.positive_percentage || 0}%`;
        
        document.getElementById('negativeCount').textContent = summary.negative || 0;
        document.getElementById('negativePercentage').textContent = `${summary.negative_percentage || 0}%`;
        
        document.getElementById('neutralCount').textContent = summary.neutral || 0;
        document.getElementById('neutralPercentage').textContent = `${summary.neutral_percentage || 0}%`;
        
        document.getElementById('totalAnalyzed').textContent = summary.total_messages || 0;
        document.getElementById('avgScore').textContent = summary.avg_score || '0.00';
        
        // Create sentiment distribution chart
        this.createSentimentDistributionChart(summary);
        
        // Create sentiment trend chart
        this.createSentimentTrendChart(data.trend || {});
    }

    createSentimentDistributionChart(summary) {
        const chartData = [{
            values: [summary.positive || 0, summary.negative || 0, summary.neutral || 0],
            labels: ['Позитивные', 'Негативные', 'Нейтральные'],
            type: 'pie',
            marker: {
                colors: ['#28a745', '#dc3545', '#6c757d']
            },
            textinfo: 'label+percent',
            textposition: 'outside'
        }];

        const layout = {
            title: '',
            showlegend: true,
            margin: { t: 30, b: 30, l: 30, r: 30 },
            height: 300
        };

        Plotly.newPlot('sentimentDistributionChart', chartData, layout, {responsive: true});
    }

    createSentimentTrendChart(trendData) {
        const chartData = [
            {
                x: trendData.labels || [],
                y: trendData.positive || [],
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Позитивные',
                line: { color: '#28a745' }
            },
            {
                x: trendData.labels || [],
                y: trendData.negative || [],
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Негативные',
                line: { color: '#dc3545' }
            },
            {
                x: trendData.labels || [],
                y: trendData.neutral || [],
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Нейтральные',
                line: { color: '#6c757d' }
            }
        ];

        const layout = {
            title: '',
            xaxis: { title: 'Дата' },
            yaxis: { title: 'Количество сообщений' },
            margin: { t: 30, b: 50, l: 50, r: 30 },
            height: 300
        };

        Plotly.newPlot('sentimentTrendChart', chartData, layout, {responsive: true});
    }

    // Communications Functions
    async loadCommunicationsData() {
        console.log('Loading communications data');
        
        const limit = document.getElementById('communicationsLimit')?.value || 50;
        const selectedChatId = this.selectedChatFilter || '';
        
        const params = new URLSearchParams({
            limit: limit,
            hours: 24
        });
        
        if (selectedChatId) {
            params.append('chat_id', selectedChatId);
        }
        
        const url = `/api/recent-communications?${params.toString()}`;
        const authHeaders = this.getAuthHeaders();
        
        try {
            const response = await fetch(url, { headers: authHeaders });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received communications data:', data);
            
            this.updateCommunicationsDisplay(data);
        } catch (error) {
            console.error('Error loading communications data:', error);
            this.showError('Ошибка загрузки коммуникаций');
        }
    }

    updateCommunicationsDisplay(data) {
        // Update chat tabs
        this.updateChatTabs(data.chats || []);
        
        // Update messages list
        this.updateMessagesList(data.messages || []);
    }

    updateChatTabs(chats) {
        const chatTabsContainer = document.getElementById('chatTabs');
        if (!chatTabsContainer) return;
        
        // Clear existing tabs except "Все чаты"
        const allChatsTab = chatTabsContainer.querySelector('[data-chat-id=""]');
        chatTabsContainer.innerHTML = '';
        if (allChatsTab) {
            chatTabsContainer.appendChild(allChatsTab);
        }
        
        // Add chat tabs
        chats.forEach(chat => {
            const tabButton = document.createElement('button');
            tabButton.className = 'chat-tab';
            tabButton.setAttribute('data-chat-id', chat.chat_id);
            tabButton.onclick = () => this.filterByChat(chat.chat_id);
            tabButton.innerHTML = `
                ${chat.title}
                <small>(${chat.message_count})</small>
            `;
            chatTabsContainer.appendChild(tabButton);
        });
    }

    updateMessagesList(messages) {
        const messagesContainer = document.getElementById('messagesList');
        if (!messagesContainer) return;
        
        if (messages.length === 0) {
            messagesContainer.innerHTML = '<div class="no-messages">Сообщения не найдены</div>';
            return;
        }
        
        messagesContainer.innerHTML = messages.map(message => `
            <div class="message-item ${message.sender_type}">
                <div class="message-avatar ${message.sender_type}">
                    ${message.sender_name.charAt(0).toUpperCase()}
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-sender">${message.sender_name}</span>
                        <div class="message-meta">
                            <span class="message-time">${message.timestamp}</span>
                            <span class="message-chat">${message.chat_title}</span>
                        </div>
                    </div>
                    <div class="message-text">${message.text || 'Медиафайл'}</div>
                    ${message.sentiment ? `
                        <div class="message-sentiment ${message.sentiment.label}">
                            <span>${message.sentiment.emoji}</span>
                            <span>${message.sentiment.label}</span>
                            <span>(${message.sentiment.score})</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    filterByChat(chatId) {
        this.selectedChatFilter = chatId;
        
        // Update active tab
        document.querySelectorAll('.chat-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`[data-chat-id="${chatId}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }
        
        // Reload communications data
        this.loadCommunicationsData();
    }
}

// Global variables
let dashboardInstance = null;

// Global functions for button controls
function toggleClientChartType(type) {
    if (dashboardInstance) {
        dashboardInstance.toggleClientChartType(type);
    }
}

function toggleClientView(viewType) {
    if (dashboardInstance) {
        dashboardInstance.toggleClientView(viewType);
    }
}

function refreshCommunications() {
    if (dashboardInstance) {
        dashboardInstance.loadCommunicationsData();
    }
}

function filterByChat(chatId) {
    if (dashboardInstance) {
        dashboardInstance.filterByChat(chatId);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Set admin token from template if available
    if (typeof adminToken !== 'undefined') {
        window.adminToken = adminToken;
    }
    
    // Initialize dashboard
    dashboardInstance = new FilteredDashboard();
});