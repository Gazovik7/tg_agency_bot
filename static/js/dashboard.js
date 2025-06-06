// Enhanced Dashboard with Filters
class FilteredDashboard {
    constructor() {
        this.adminToken = window.adminToken || '771G@zoviK';
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

        // Chart period buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('chart-period-btn')) {
                this.handleChartPeriodChange(e.target);
            }
        });

        // Tab change events - using new tab system
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remove active class from all tabs
                tabButtons.forEach(t => t.classList.remove('active'));
                
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
        
        // Update TOP lists
        this.updateTopLists(data.clients);
        
        // Create additional dashboard charts only once
        if (!this.charts.sentimentTrendChart) {
            this.createSentimentTrendChart(data);
        } else {
            this.updateSentimentTrendChart(data);
        }
        
        if (!this.charts.responseTimeTrendChart) {
            this.createResponseTimeTrendChart(data);
        } else {
            this.updateResponseTimeTrendChart(data);
        }
        
        // Create charts based on current tab
        const activeTab = document.querySelector('#dashboardTabs .nav-link.active');
        if (activeTab) {
            const tabId = activeTab.getAttribute('data-bs-target').replace('#', '');
            this.handleTabChange(tabId);
        }
    }

    updateGeneralStats(stats) {
        // Update statistics cards for new design
        const elements = {
            'totalMessages': stats.total_messages || 0,
            'clientMessages': stats.client_messages || 0,
            'teamMessages': stats.team_messages || 0,
            'totalCharacters': this.formatNumber(stats.total_symbols || 0),
            'medianResponseTime': this.formatTime(stats.median_response_time_minutes || 0),
            'maxResponseTime': this.formatTime(stats.max_response_time_minutes || 0),
            'avgSentimentScore': (stats.avg_sentiment_score || 0).toFixed(2),
            'activeClients': stats.active_clients || 0
        };

        Object.keys(elements).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = elements[id];
            }
        });

        // Update percentages
        const total = stats.total_messages || 0;
        const clientPercent = total > 0 ? Math.round((stats.client_messages / total) * 100) : 0;
        const teamPercent = total > 0 ? Math.round((stats.team_messages / total) * 100) : 0;

        const clientPercentElement = document.getElementById('clientPercent');
        if (clientPercentElement) {
            clientPercentElement.textContent = `${clientPercent}% от общего`;
        }

        const teamPercentElement = document.getElementById('teamPercent');
        if (teamPercentElement) {
            teamPercentElement.textContent = `${teamPercent}% от общего`;
        }
    }

    updateEmployeesTab(employees) {
        try {
            console.log('Updating employees tab with data:', employees);
            
            // Create employee activity chart
            if (employees && employees.length > 0) {
                this.createEmployeeChart(employees);
                this.updateEmployeesTable(employees);
            } else {
                console.log('No employees data, showing empty state');
                // Show empty state
                const chartContainer = document.getElementById('employeeActivityChart');
                if (chartContainer) {
                    chartContainer.innerHTML = '<div class="text-center text-gray-500 py-8">Нет данных о сотрудниках</div>';
                }
                
                const tableBody = document.getElementById('employeesTableBody');
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-gray-500 py-8">Нет данных о сотрудниках</td></tr>';
                }
            }
        } catch (error) {
            console.error('Error updating employees tab:', error);
            console.error('Error details:', error.message, error.stack);
        }
    }

    updateEmployeesTable(employees) {
        const tableBody = document.getElementById('employeesTableBody');
        if (!tableBody) return;

        const rows = employees.map(employee => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center mr-3">
                            <span class="text-purple-600 text-sm font-medium">${(employee.name || employee.full_name || 'Н/А').charAt(0)}</span>
                        </div>
                        <div>
                            <div class="text-sm font-medium text-gray-900">${this.escapeHtml(employee.name || employee.full_name || 'Неизвестно')}</div>
                            <div class="text-sm text-gray-500">${this.escapeHtml(employee.role || 'Сотрудник')}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${employee.message_count || 0}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${this.formatNumber(employee.character_count || 0)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${employee.avg_response_time ? Math.round(employee.avg_response_time) + ' мин' : '—'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${this.getActivityBadgeClass(employee.message_count || 0)}">
                        ${this.getActivityLevel(employee.message_count || 0)}
                    </span>
                </td>
            </tr>
        `).join('');

        tableBody.innerHTML = rows;
    }

    getActivityBadgeClass(messageCount) {
        if (messageCount >= 50) return 'bg-green-100 text-green-800';
        if (messageCount >= 20) return 'bg-yellow-100 text-yellow-800';
        if (messageCount >= 5) return 'bg-blue-100 text-blue-800';
        return 'bg-gray-100 text-gray-800';
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
            cardsContainer.innerHTML = '<div class="col-span-full text-center text-gray-500 py-8">Нет данных о клиентах за выбранный период</div>';
            return;
        }

        // Сортируем клиентов по активности
        const sortedClients = [...clients].sort((a, b) => b.total_messages - a.total_messages);

        sortedClients.forEach((client, index) => {
            const priorityClass = this.getClientPriority(client);
            const responseTimeClass = this.getResponseTimeClass(client.avg_response_time_minutes);
            
            const card = document.createElement('div');
            card.className = 'client-card bg-white rounded-xl p-6 shadow-sm border';
            card.innerHTML = `
                <div class="flex items-start justify-between mb-4">
                    <h4 class="text-lg font-semibold text-gray-900 leading-tight">${this.escapeHtml(client.name)}</h4>
                    <span class="px-2 py-1 text-xs font-medium rounded-full ${priorityClass.class}">${priorityClass.label}</span>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600">${client.total_messages}</div>
                        <div class="text-xs text-gray-500 uppercase tracking-wide">Сообщений</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-purple-600">${Math.round(client.communication_intensity || 0)}</div>
                        <div class="text-xs text-gray-500 uppercase tracking-wide">Интенсивность</div>
                    </div>
                </div>

                <div class="mb-4 p-3 rounded-lg ${responseTimeClass}">
                    <div class="flex items-center gap-2">
                        <i class="fas fa-clock"></i>
                        <span class="font-medium">Время ответа:</span>
                        <span>${this.formatResponseTimeText(client.avg_response_time_minutes)}</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3 mb-4">
                    <div class="bg-blue-50 rounded-lg p-3 text-center">
                        <div class="text-sm text-blue-600 font-medium">Наша команда</div>
                        <div class="text-xl font-bold text-blue-800">${client.team_messages}</div>
                        <div class="text-xs text-blue-600">${client.team_characters} симв.</div>
                    </div>
                    <div class="bg-purple-50 rounded-lg p-3 text-center">
                        <div class="text-sm text-purple-600 font-medium">Клиент</div>
                        <div class="text-xl font-bold text-purple-800">${client.client_messages}</div>
                        <div class="text-xs text-purple-600">${client.client_characters} симв.</div>
                    </div>
                </div>

                <div class="flex gap-2">
                    <div class="flex-1 bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded text-center">
                        &lt; 5 мин: ${client.responses_under_5min || 0}
                    </div>
                    <div class="flex-1 bg-orange-100 text-orange-800 text-xs font-medium px-2 py-1 rounded text-center">
                        &gt; 1 час: ${client.responses_over_1hour || 0}
                    </div>
                </div>
            `;
            cardsContainer.appendChild(card);
        });
    }

    getClientPriority(client) {
        const avgResponseTime = client.avg_response_time_minutes || 0;
        const totalMessages = client.total_messages || 0;
        
        if (avgResponseTime > 240 || totalMessages > 50) {
            return { class: 'bg-red-100 text-red-800', label: 'Высокий' };
        } else if (avgResponseTime > 60 || totalMessages > 25) {
            return { class: 'bg-yellow-100 text-yellow-800', label: 'Средний' };
        } else {
            return { class: 'bg-green-100 text-green-800', label: 'Низкий' };
        }
    }

    getResponseTimeClass(minutes) {
        if (!minutes || minutes === 0) return 'bg-gray-100 text-gray-600';
        if (minutes <= 15) return 'bg-green-100 text-green-800';
        if (minutes <= 60) return 'bg-yellow-100 text-yellow-800';
        return 'bg-red-100 text-red-800';
    }

    formatResponseTimeText(minutes) {
        if (!minutes || minutes === 0) {
            return 'Не определено';
        }
        
        if (minutes >= 60) {
            const hours = Math.floor(minutes / 60);
            const remainingMinutes = Math.round(minutes % 60);
            return `${hours}ч ${remainingMinutes}м`;
        } else {
            return `${Math.round(minutes)}м`;
        }
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
    async loadActivityData(grouping = 'day') {
        try {
            // Use the grouping parameter passed to the function
            console.log('Loading activity data with grouping:', grouping);
            
            console.log('Loading activity data with filters:', this.currentFilters, 'grouping:', grouping);

            // Build URL parameters manually to avoid issues
            const params = new URLSearchParams();
            Object.entries(this.currentFilters).forEach(([key, value]) => {
                if (value) params.append(key, value);
            });
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
        // Check if we have data
        if (!data) {
            console.log('No activity data received');
            return;
        }
        
        // Update key metrics if available
        if (data.metrics) {
            this.updateActivityMetrics(data.metrics, grouping);
        }
        
        // Create charts if containers exist and data is available
        const timeSeriesContainer = document.getElementById('activityTimeSeriesChart');
        if (timeSeriesContainer && data.timeSeries) {
            console.log('Creating time series chart with data:', data.timeSeries);
            this.createActivityTimeSeries(data.timeSeries, grouping);
        }
        
        const hourHistogramContainer = document.getElementById('activityHourHistogram');
        if (hourHistogramContainer && data.hourDistribution) {
            console.log('Creating hour histogram with data:', data.hourDistribution);
            this.createActivityHourHistogram(data.hourDistribution);
        }
        
        const heatmapsContainer = document.getElementById('activityClientHeatmap');
        if (heatmapsContainer && data.heatmaps) {
            console.log('Creating heatmaps with data:', data.heatmaps);
            this.createActivityHeatmaps(data.heatmaps);
        }
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

    formatTime(minutes) {
        if (!minutes || minutes === 0) {
            return '0 мин';
        }
        if (minutes < 60) {
            return `${Math.round(minutes)} мин`;
        } else {
            const hours = Math.floor(minutes / 60);
            const remainingMinutes = Math.round(minutes % 60);
            if (remainingMinutes === 0) {
                return `${hours}ч`;
            }
            return `${hours}ч ${remainingMinutes}мин`;
        }
    }

    updateTopLists(clients) {
        // Фильтруем клиентов с данными о тональности
        const clientsWithSentiment = clients.filter(client => 
            client.avg_sentiment !== undefined && client.avg_sentiment !== null
        );

        // ТОП-5 негативных клиентов (по минимальной тональности)
        const negativeClients = [...clientsWithSentiment]
            .sort((a, b) => a.avg_sentiment - b.avg_sentiment)
            .slice(0, 5);
        this.renderTopList('topNegativeClients', negativeClients, 'negative');

        // ТОП-5 позитивных клиентов (по максимальной тональности) 
        const positiveClients = [...clientsWithSentiment]
            .sort((a, b) => b.avg_sentiment - a.avg_sentiment)
            .slice(0, 5);
        this.renderTopList('topPositiveClients', positiveClients, 'positive');

        // ТОП-5 по объему коммуникаций (по количеству сообщений)
        const activeClients = [...clients]
            .sort((a, b) => b.total_messages - a.total_messages)
            .slice(0, 5);
        this.renderTopList('topActiveClients', activeClients, 'active');

        // ТОП-5 с наибольшим временем ответа (по максимальному времени)
        const slowResponseClients = [...clients]
            .filter(client => client.max_response_time_minutes > 0)
            .sort((a, b) => b.max_response_time_minutes - a.max_response_time_minutes)
            .slice(0, 5);
        this.renderTopList('topSlowResponseClients', slowResponseClients, 'slow');
    }

    renderTopList(containerId, clients, type) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const items = clients.map((client, index) => {
            const initials = this.getClientInitials(client.name);
            let metricValue = '';
            let metricClass = '';

            switch (type) {
                case 'negative':
                    metricValue = client.avg_sentiment.toFixed(2);
                    metricClass = 'sentiment-negative px-3 py-1 rounded-full text-sm font-semibold';
                    break;
                case 'positive':
                    metricValue = client.avg_sentiment.toFixed(2);
                    metricClass = 'sentiment-positive px-3 py-1 rounded-full text-sm font-semibold';
                    break;
                case 'active':
                    metricValue = `${client.total_messages} сооб.`;
                    metricClass = 'bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold';
                    break;
                case 'slow':
                    metricValue = this.formatTime(client.max_response_time_minutes);
                    metricClass = 'bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold';
                    break;
            }

            return `
                <div class="top-list-item flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 transition-colors">
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                            <span class="text-sm font-semibold">${initials}</span>
                        </div>
                        <div>
                            <p class="font-medium text-gray-900">${this.escapeHtml(client.name)}</p>
                            <p class="text-sm text-gray-500">${client.total_messages} сообщений</p>
                        </div>
                    </div>
                    <div class="${metricClass}">
                        ${metricValue}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = items || '<p class="text-gray-500 text-sm">Нет данных</p>';
    }

    getClientInitials(name) {
        if (!name) return 'НД';
        const words = name.split(' ').filter(word => word.length > 0);
        if (words.length >= 2) {
            return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
        }
        return words[0].charAt(0).toUpperCase() + (words[0].charAt(1) || '').toUpperCase();
    }

    createSentimentTrendChart(data) {
        let ctx = document.getElementById('sentimentTrendChart');
        if (!ctx) {
            console.log('Sentiment trend chart canvas not found');
            return;
        }
        
        // Проверяем, что это действительно Canvas элемент
        if (ctx.tagName !== 'CANVAS') {
            console.error('Element sentimentTrendChart is not a canvas:', ctx.tagName);
            return;
        }

        // Уничтожаем существующий график если есть
        if (this.charts.sentimentTrendChart) {
            this.charts.sentimentTrendChart.destroy();
            this.charts.sentimentTrendChart = null;
        }

        // Полностью пересоздаем Canvas элемент для избежания конфликтов Chart.js
        const parent = ctx.parentNode;
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'sentimentTrendChart';
        newCanvas.style.width = '100%';
        newCanvas.style.height = '400px';
        parent.removeChild(ctx);
        parent.appendChild(newCanvas);
        ctx = newCanvas;

        console.log('Creating sentiment trend chart...');

        // Проверяем, что Canvas не занят
        try {
            // Получаем реальные данные тренда тональности
            this.loadSentimentTrendData().then(trendData => {
                console.log('Creating sentiment chart with data:', trendData);
                
                // Принудительная очистка Canvas перед созданием нового графика
                try {
                    const context = ctx.getContext('2d');
                    context.clearRect(0, 0, ctx.width, ctx.height);
                } catch (e) {
                    console.log('Canvas clear failed, trying canvas recreation');
                    // Если очистка не помогла, пересоздаем Canvas
                    const parent = ctx.parentNode;
                    const newCanvas = document.createElement('canvas');
                    newCanvas.id = 'sentimentTrendChart';
                    newCanvas.style.width = '100%';
                    newCanvas.style.height = '400px';
                    parent.removeChild(ctx);
                    parent.appendChild(newCanvas);
                    ctx = newCanvas;
                }

                this.charts.sentimentTrendChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: trendData.labels || [],
                        datasets: [{
                            label: 'Средняя тональность',
                            data: trendData.data || [],
                            borderColor: 'rgb(16, 185, 129)',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: false,
                                min: -1,
                                max: 1,
                                ticks: {
                                    callback: function(value) {
                                        return value.toFixed(1);
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    }
                });
            }).catch(error => {
                console.error('Error creating sentiment trend chart:', error);
                if (ctx && ctx.parentElement) {
                    ctx.parentElement.innerHTML = '<div class="text-center text-gray-500 py-8">Ошибка создания графика тональности</div>';
                }
            });
        } catch (error) {
            console.error('Error creating sentiment trend chart:', error);
        }
    }

    async loadSentimentTrendData() {
        try {
            console.log('Loading sentiment trend data with token:', this.adminToken);
            const response = await fetch('/api/sentiment-trend?days=7', {
                headers: { 'X-Admin-Token': this.adminToken }
            });
            
            console.log('Sentiment trend response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Sentiment trend API error:', response.status, errorText);
                throw new Error('Failed to fetch sentiment trend data: ' + response.status);
            }
            
            const data = await response.json();
            console.log('Sentiment trend data loaded:', data);
            return data;
        } catch (error) {
            console.error('Error loading sentiment trend data:', error);
            return { labels: [], data: [] };
        }
    }

    async loadResponseTimeTrendData() {
        try {
            console.log('Loading response time trend data with token:', this.adminToken);
            const response = await fetch('/api/response-time-trend?days=7', {
                headers: { 'X-Admin-Token': this.adminToken }
            });
            
            console.log('Response time trend response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Response time trend API error:', response.status, errorText);
                throw new Error('Failed to fetch response time trend data: ' + response.status);
            }
            
            const data = await response.json();
            console.log('Response time trend data loaded:', data);
            return data;
        } catch (error) {
            console.error('Error loading response time trend data:', error);
            return { labels: [], data: [] };
        }
    }

    async updateSentimentTrendChart(data) {
        if (!this.charts.sentimentTrendChart) return;

        try {
            // Получаем реальные данные тренда тональности
            const trendData = await this.loadSentimentTrendData();

            // Обновляем данные графика
            this.charts.sentimentTrendChart.data.labels = trendData.labels || [];
            this.charts.sentimentTrendChart.data.datasets[0].data = trendData.data || [];
            this.charts.sentimentTrendChart.update();
        } catch (error) {
            console.error('Error updating sentiment trend chart:', error);
        }
    }

    createResponseTimeTrendChart(data) {
        let ctx = document.getElementById('responseTimeTrendChart');
        if (!ctx) {
            console.log('Response time trend chart canvas not found');
            return;
        }
        
        // Проверяем, что это действительно Canvas элемент
        if (ctx.tagName !== 'CANVAS') {
            console.error('Element responseTimeTrendChart is not a canvas:', ctx.tagName);
            return;
        }

        // Уничтожаем существующий график если есть
        if (this.charts.responseTimeTrendChart) {
            this.charts.responseTimeTrendChart.destroy();
            this.charts.responseTimeTrendChart = null;
        }

        // Полностью пересоздаем Canvas элемент для избежания конфликтов Chart.js
        const parent = ctx.parentNode;
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'responseTimeTrendChart';
        newCanvas.style.width = '100%';
        newCanvas.style.height = '400px';
        parent.removeChild(ctx);
        parent.appendChild(newCanvas);
        ctx = newCanvas;

        try {
            // Получаем реальные данные тренда времени ответа
            this.loadResponseTimeTrendData().then(trendData => {
                console.log('Creating response time chart with data:', trendData);
                
                // Принудительная очистка Canvas перед созданием нового графика
                try {
                    const context = ctx.getContext('2d');
                    context.clearRect(0, 0, ctx.width, ctx.height);
                } catch (e) {
                    console.log('Canvas clear failed, trying canvas recreation');
                    // Если очистка не помогла, пересоздаем Canvas
                    const parent = ctx.parentNode;
                    const newCanvas = document.createElement('canvas');
                    newCanvas.id = 'responseTimeTrendChart';
                    newCanvas.style.width = '100%';
                    newCanvas.style.height = '400px';
                    parent.removeChild(ctx);
                    parent.appendChild(newCanvas);
                    ctx = newCanvas;
                }

                this.charts.responseTimeTrendChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: trendData.labels || [],
                        datasets: [{
                            label: 'Среднее время ответа (мин)',
                            data: trendData.data || [],
                            borderColor: 'rgb(245, 158, 11)',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        return value + ' мин';
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    }
                });
            }).catch(error => {
                console.error('Error creating response time trend chart:', error);
                if (ctx && ctx.parentElement) {
                    ctx.parentElement.innerHTML = '<div class="text-center text-gray-500 py-8">Ошибка создания графика времени ответа</div>';
                }
            });
        } catch (error) {
            console.error('Error creating response time trend chart:', error);
        }
    }

    async updateResponseTimeTrendChart(data) {
        if (!this.charts.responseTimeTrendChart) return;

        try {
            // Получаем реальные данные тренда времени ответа
            const trendData = await this.loadResponseTimeTrendData();

            // Обновляем данные графика
            this.charts.responseTimeTrendChart.data.labels = trendData.labels || [];
            this.charts.responseTimeTrendChart.data.datasets[0].data = trendData.data || [];
            this.charts.responseTimeTrendChart.update();
        } catch (error) {
            console.error('Error updating response time trend chart:', error);
        }
    }

    handleChartPeriodChange(button) {
        const chartType = button.getAttribute('data-chart');
        const period = button.getAttribute('data-period');
        
        // Update button states for this chart
        const chartButtons = document.querySelectorAll(`[data-chart="${chartType}"]`);
        chartButtons.forEach(btn => {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('bg-gray-100', 'text-gray-700');
        });
        
        button.classList.remove('bg-gray-100', 'text-gray-700');
        button.classList.add('bg-blue-600', 'text-white');
        
        // Update chart data based on period
        if (chartType === 'sentiment') {
            this.updateSentimentChartPeriod(period);
        } else if (chartType === 'response-time') {
            this.updateResponseTimeChartPeriod(period);
        }
    }

    updateSentimentChartPeriod(period) {
        if (!this.charts.sentimentTrendChart) return;
        
        // Используем текущий временной диапазон из фильтров
        const startDate = new Date(this.currentFilters.start_date);
        const endDate = new Date(this.currentFilters.end_date);
        
        const labels = [];
        const data = [];
        
        // Группируем данные в зависимости от выбранного периода
        if (period === 'day') {
            // Группировка по дням в рамках выбранного периода
            const currentDate = new Date(startDate);
            while (currentDate <= endDate) {
                labels.push(currentDate.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }));
                // Здесь должны быть реальные данные из базы, пока используем демо-данные
                data.push((Math.random() - 0.5) * 1.5);
                currentDate.setDate(currentDate.getDate() + 1);
            }
        } else if (period === 'week') {
            // Группировка по неделям
            const currentDate = new Date(startDate);
            currentDate.setDate(currentDate.getDate() - currentDate.getDay()); // Начало недели
            
            while (currentDate <= endDate) {
                // Вычисляем номер недели в году
                const weekNumber = this.getWeekNumber(currentDate);
                labels.push(`Неделя ${weekNumber}`);
                data.push((Math.random() - 0.5) * 1.5);
                currentDate.setDate(currentDate.getDate() + 7);
            }
        } else if (period === 'month') {
            // Группировка по месяцам
            const currentDate = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
            
            while (currentDate <= endDate) {
                labels.push(currentDate.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' }));
                data.push((Math.random() - 0.5) * 1.5);
                currentDate.setMonth(currentDate.getMonth() + 1);
            }
        }
        
        this.charts.sentimentTrendChart.data.labels = labels;
        this.charts.sentimentTrendChart.data.datasets[0].data = data;
        this.charts.sentimentTrendChart.update();
    }

    updateResponseTimeChartPeriod(period) {
        if (!this.charts.responseTimeTrendChart) return;
        
        // Используем текущий временной диапазон из фильтров
        const startDate = new Date(this.currentFilters.start_date);
        const endDate = new Date(this.currentFilters.end_date);
        
        const labels = [];
        const data = [];
        
        // Группируем данные в зависимости от выбранного периода
        if (period === 'day') {
            // Группировка по дням в рамках выбранного периода
            const currentDate = new Date(startDate);
            while (currentDate <= endDate) {
                labels.push(currentDate.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }));
                // Здесь должны быть реальные данные из базы, пока используем демо-данные
                data.push(Math.random() * 150 + 50); // 50-200 минут
                currentDate.setDate(currentDate.getDate() + 1);
            }
        } else if (period === 'week') {
            // Группировка по неделям
            const currentDate = new Date(startDate);
            currentDate.setDate(currentDate.getDate() - currentDate.getDay()); // Начало недели
            
            while (currentDate <= endDate) {
                // Вычисляем номер недели в году
                const weekNumber = this.getWeekNumber(currentDate);
                labels.push(`Неделя ${weekNumber}`);
                data.push(Math.random() * 150 + 50);
                currentDate.setDate(currentDate.getDate() + 7);
            }
        } else if (period === 'month') {
            // Группировка по месяцам
            const currentDate = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
            
            while (currentDate <= endDate) {
                labels.push(currentDate.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' }));
                data.push(Math.random() * 150 + 50);
                currentDate.setMonth(currentDate.getMonth() + 1);
            }
        }
        
        this.charts.responseTimeTrendChart.data.labels = labels;
        this.charts.responseTimeTrendChart.data.datasets[0].data = data;
        this.charts.responseTimeTrendChart.update();
    }

    // Utility function to get week number in year
    getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
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

    loadTabData(tabName) {
        switch(tabName) {
            case 'dashboard':
                this.loadDashboardData();
                break;
            case 'clients':
                this.loadDashboardData(); // Clients data is part of dashboard data
                break;
            case 'activity':
                this.loadActivityData('day');
                break;
            case 'sentiment':
                this.loadSentimentData();
                break;
            case 'communications':
                this.loadCommunicationsData();
                break;
            case 'employees':
                // Load employees data if needed
                break;
        }
    }

    applyFilters() {
        // Update current filters from form
        this.currentFilters.start_date = document.getElementById('startDate').value;
        this.currentFilters.end_date = document.getElementById('endDate').value;
        this.currentFilters.chat_id = document.getElementById('chatFilter').value;
        this.currentFilters.employee_id = document.getElementById('employeeFilter').value;
        
        // Reload data for current tab
        const activeTab = document.querySelector('.tab-button.active');
        if (activeTab) {
            const tabName = activeTab.dataset.tab;
            this.loadTabData(tabName);
        } else {
            this.loadDashboardData();
        }
    }

    refreshCommunications() {
        this.loadCommunicationsData();
    }

    toggleClientView(viewType) {
        const cardsView = document.getElementById('clientCardsView');
        const tableView = document.getElementById('clientTableView');

        if (viewType === 'cards') {
            cardsView.classList.remove('hidden');
            tableView.classList.add('hidden');
        } else {
            cardsView.classList.add('hidden');
            tableView.classList.remove('hidden');
        }
    }

    toggleClientChartType(type) {
        // Implement chart type switching if needed
        console.log('Toggle chart type to:', type);
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
        try {
            const summary = data.summary || {};
            
            // Update sentiment statistics - using new design element IDs
            const positiveCountEl = document.getElementById('positiveCount');
            if (positiveCountEl) positiveCountEl.textContent = summary.positive || 0;
            
            const positivePercentEl = document.getElementById('positivePercent');
            if (positivePercentEl) positivePercentEl.textContent = `${summary.positive_percentage || 0}%`;
            
            const negativeCountEl = document.getElementById('negativeCount');
            if (negativeCountEl) negativeCountEl.textContent = summary.negative || 0;
            
            const negativePercentEl = document.getElementById('negativePercent');
            if (negativePercentEl) negativePercentEl.textContent = `${summary.negative_percentage || 0}%`;
            
            const neutralCountEl = document.getElementById('neutralCount');
            if (neutralCountEl) neutralCountEl.textContent = summary.neutral || 0;
            
            const neutralPercentEl = document.getElementById('neutralPercent');
            if (neutralPercentEl) neutralPercentEl.textContent = `${summary.neutral_percentage || 0}%`;
            
            const totalAnalyzedEl = document.getElementById('totalAnalyzed');
            if (totalAnalyzedEl) totalAnalyzedEl.textContent = `${summary.total_messages || 0} проанализировано`;
            
            const avgScoreEl = document.getElementById('avgScore');
            if (avgScoreEl) avgScoreEl.textContent = summary.avg_score || '0.00';
            
            // Create sentiment distribution chart
            this.createSentimentDistributionChart(summary);
            
            // Create sentiment trend chart
            this.createSentimentTrendChart(data.trend || {});
        } catch (error) {
            console.error('Error updating sentiment display:', error);
        }
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
        try {
            console.log('Updating communications display with data:', data);
            
            if (data.chats && data.chats.length > 0) {
                this.updateChatTabs(data.chats);
            } else {
                console.log('No chats data available');
            }
            
            if (data.messages && data.messages.length > 0) {
                this.updateMessagesList(data.messages);
            } else {
                console.log('No messages data available');
                // Show empty state message
                const messagesContainer = document.getElementById('messagesList');
                if (messagesContainer) {
                    messagesContainer.innerHTML = '<div class="text-center text-gray-500 py-8">Нет сообщений для отображения</div>';
                }
            }
        } catch (error) {
            console.error('Error updating communications display:', error);
        }
    }

    updateChatTabs(chats) {
        const chatTabsContainer = document.getElementById('chatsContainer');
        if (!chatTabsContainer) {
            console.log('Chat tabs container not found');
            return;
        }
        
        // Clear existing tabs except "Все чаты"
        const allChatsTab = chatTabsContainer.querySelector('[data-chat-id=""]');
        chatTabsContainer.innerHTML = '';
        if (allChatsTab) {
            chatTabsContainer.appendChild(allChatsTab);
        }
        
        // Add chat cards for new design
        const chatCards = chats.map(chat => `
            <div class="bg-white rounded-lg p-4 border border-gray-200 hover:shadow-md transition-shadow cursor-pointer chat-card" data-chat-id="${chat.chat_id}">
                <div class="flex items-center justify-between mb-2">
                    <h5 class="font-medium text-gray-900 truncate">${this.escapeHtml(chat.title)}</h5>
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        ${chat.message_count}
                    </span>
                </div>
                <div class="flex justify-between text-sm text-gray-500">
                    <span>Клиенты: ${chat.client_messages}</span>
                    <span>Команда: ${chat.team_messages}</span>
                </div>
                <div class="text-xs text-gray-400 mt-1">
                    Последняя активность: ${chat.last_activity}
                </div>
            </div>
        `).join('');
        
        chatTabsContainer.innerHTML = chatCards;
        
        // Add click handlers for chat cards
        chatTabsContainer.querySelectorAll('.chat-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const chatId = card.getAttribute('data-chat-id');
                this.filterByChat(chatId);
                
                // Update active state
                chatTabsContainer.querySelectorAll('.chat-card').forEach(c => c.classList.remove('ring-2', 'ring-blue-500'));
                card.classList.add('ring-2', 'ring-blue-500');
            });
        });
    }

    updateMessagesList(messages) {
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) {
            console.log('Messages container not found');
            return;
        }
        
        if (messages.length === 0) {
            messagesContainer.innerHTML = '<div class="text-center text-gray-500 py-8">Сообщения не найдены</div>';
            return;
        }
        
        const messageCards = messages.map(message => `
            <div class="bg-white rounded-lg p-4 border border-gray-200 hover:shadow-sm transition-shadow">
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${message.sender_type === 'client' ? 'bg-blue-500' : 'bg-green-500'}">
                        ${message.sender_name.charAt(0).toUpperCase()}
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between mb-1">
                            <p class="text-sm font-medium text-gray-900 truncate">${this.escapeHtml(message.sender_name)}</p>
                            <p class="text-xs text-gray-500">${message.timestamp}</p>
                        </div>
                        <p class="text-sm text-gray-600 mb-2">${this.escapeHtml(message.text || 'Медиафайл')}</p>
                        <div class="flex items-center justify-between">
                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${message.sender_type === 'client' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}">
                                ${message.sender_type === 'client' ? 'Клиент' : 'Команда'}
                            </span>
                            <span class="text-xs text-gray-400">${this.escapeHtml(message.chat_title)}</span>
                        </div>
                        ${message.sentiment ? `
                            <div class="mt-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${this.getSentimentBadgeClass(message.sentiment.label)}">
                                <span class="mr-1">${this.getSentimentEmoji(message.sentiment.label)}</span>
                                ${message.sentiment.label} (${message.sentiment.score})
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');
        
        messagesContainer.innerHTML = messageCards;
    }

    getSentimentBadgeClass(label) {
        switch(label.toLowerCase()) {
            case 'positive': return 'bg-green-100 text-green-800';
            case 'negative': return 'bg-red-100 text-red-800';
            case 'neutral': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    }

    getSentimentEmoji(label) {
        switch(label.toLowerCase()) {
            case 'positive': return '😊';
            case 'negative': return '😠';
            case 'neutral': return '😐';
            default: return '📊';
        }
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