// Dashboard JavaScript functionality
class DashboardManager {
    constructor() {
        this.apiToken = this.getApiToken();
        this.refreshInterval = 300000; // 5 minutes
        this.autoRefreshTimer = null;
        this.charts = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadDashboardData();
        this.startAutoRefresh();
    }
    
    getApiToken() {
        // Get admin token from environment or prompt user
        let token = localStorage.getItem('adminToken');
        if (!token) {
            token = prompt('Enter admin token:');
            if (token) {
                localStorage.setItem('adminToken', token);
            }
        }
        return token;
    }
    
    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadDashboardData();
        });
        
        // Tab change events
        const tabs = document.querySelectorAll('#dashboardTabs button[data-bs-toggle="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.handleTabChange(e.target.id);
            });
        });
        
        // Error modal retry
        const retryBtn = document.querySelector('#errorModal .btn-primary');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.loadDashboardData();
            });
        }
    }
    
    startAutoRefresh() {
        this.autoRefreshTimer = setInterval(() => {
            this.loadDashboardData(false); // Silent refresh
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
        }
    }
    
    async loadDashboardData(showLoading = true) {
        if (showLoading) {
            this.showLoadingModal();
        }
        
        try {
            if (!this.apiToken) {
                this.apiToken = this.getApiToken();
            }
            
            const headers = {
                'Content-Type': 'application/json'
            };
            
            if (this.apiToken) {
                headers['Authorization'] = `Bearer ${this.apiToken}`;
            }
            
            const response = await fetch('/dashboard-data', {
                headers: headers
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    this.handleAuthError();
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.updateDashboard(data);
            this.hideLoadingModal();
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.hideLoadingModal();
            this.showError(error.message);
        }
    }
    
    updateDashboard(data) {
        this.updateSummaryCards(data.summary);
        this.updateAttentionAlerts(data.attention_chats);
        this.updateActivityTab(data.activity);
        this.updateSentimentTab(data.sentiment);
        this.updateTeamTab(data.team_performance);
        this.updateClientsTab(data.client_stats);
        this.updateCommunicationsTab(data);
        this.updateLastUpdated(data.last_updated);
    }
    
    updateSummaryCards(summary) {
        const elements = {
            'totalChats': summary.total_chats || 0,
            'attentionChats': summary.chats_needing_attention || 0,
            'avgResponse': this.formatTime(summary.avg_response_time),
            'totalMessages': summary.total_messages || 0
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                element.classList.add('updated');
                setTimeout(() => element.classList.remove('updated'), 1000);
            }
        });
    }
    
    updateAttentionAlerts(attentionChats) {
        const alertsContainer = document.getElementById('attentionAlerts');
        const alertsRow = document.getElementById('attentionAlertsRow');
        
        if (!attentionChats || attentionChats.length === 0) {
            alertsRow.style.display = 'none';
            return;
        }
        
        alertsRow.style.display = 'block';
        alertsContainer.innerHTML = '';
        
        attentionChats.forEach(chat => {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'attention-item';
            
            const reasons = chat.reasons.join(', ');
            const responseTime = this.formatTime(chat.avg_response_time);
            
            alertDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${this.escapeHtml(chat.chat_title)}</h6>
                        <p class="mb-1 text-warning">${reasons}</p>
                        <small class="text-muted">
                            Avg Response: ${responseTime} | 
                            Unanswered: ${chat.unanswered_percentage.toFixed(1)}%
                        </small>
                    </div>
                    <span class="badge bg-danger">${chat.negative_messages} negative</span>
                </div>
            `;
            
            alertsContainer.appendChild(alertDiv);
        });
    }
    
    updateActivityTab(activityData) {
        if (!activityData) return;
        
        // Update summary counts
        document.getElementById('clientMessagesCount').textContent = activityData.client_messages || 0;
        document.getElementById('teamMessagesCount').textContent = activityData.team_messages || 0;
        
        const totalMessages = activityData.total_messages || 0;
        const responseRate = totalMessages > 0 ? 
            ((activityData.team_messages || 0) / (activityData.client_messages || 1) * 100).toFixed(1) : 0;
        document.getElementById('responseRate').textContent = `${responseRate}%`;
        
        // Create activity chart
        this.createActivityChart(activityData.hourly_chart);
    }
    
    updateSentimentTab(sentimentData) {
        if (!sentimentData) return;
        
        this.createSentimentChart(sentimentData.distribution_chart);
        this.createSentimentTrendChart(sentimentData.trend_chart);
    }
    
    updateTeamTab(teamPerformance) {
        const tableBody = document.getElementById('teamPerformanceTable');
        tableBody.innerHTML = '';
        
        if (!teamPerformance || teamPerformance.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No team performance data available</td></tr>';
            return;
        }
        
        teamPerformance.forEach(member => {
            const row = document.createElement('tr');
            const responseTime = this.formatTime(member.avg_response_time);
            const performance = this.getPerformanceRating(member.avg_response_time);
            
            row.innerHTML = `
                <td>${this.escapeHtml(member.name)}</td>
                <td>${this.escapeHtml(member.role)}</td>
                <td>${member.message_count}</td>
                <td>${responseTime}</td>
                <td><span class="badge ${performance.class}">${performance.label}</span></td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    updateClientsTab(clientStats) {
        if (!clientStats) return;
        
        document.getElementById('uniqueClients').textContent = clientStats.total_unique_clients || 0;
        
        const tableBody = document.getElementById('activeClientsTable');
        tableBody.innerHTML = '';
        
        if (!clientStats.most_active || clientStats.most_active.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="3" class="text-center">No client data available</td></tr>';
            return;
        }
        
        clientStats.most_active.forEach(client => {
            const row = document.createElement('tr');
            const lastMessage = new Date(client.last_message).toLocaleString();
            
            row.innerHTML = `
                <td>${this.escapeHtml(client.name)}</td>
                <td>${client.message_count}</td>
                <td>${lastMessage}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    updateCommunicationsTab(data) {
        if (!data.activity) return;
        
        const clientMessages = data.activity.client_messages || 0;
        const teamMessages = data.activity.team_messages || 0;
        const totalMessages = data.activity.total_messages || 0;
        
        // Update communication metrics
        const ratio = teamMessages > 0 ? `${(clientMessages / teamMessages).toFixed(1)}:1` : 'N/A';
        document.getElementById('clientTeamRatio').textContent = ratio;
        
        const messagesPerHour = (totalMessages / 24).toFixed(1);
        document.getElementById('messagesPerHour').textContent = messagesPerHour;
        
        // Find peak hour from activity data
        const hourlyData = data.activity.hourly_chart;
        if (hourlyData && hourlyData.labels && hourlyData.datasets) {
            const peakHour = this.findPeakHour(hourlyData);
            document.getElementById('peakHour').textContent = peakHour;
        }
        
        this.createCommunicationsChart(clientMessages, teamMessages);
    }
    
    createActivityChart(chartData) {
        if (!chartData || !chartData.labels) return;
        
        const trace1 = {
            x: chartData.labels,
            y: chartData.datasets[0].data,
            name: 'Client Messages',
            type: 'bar',
            marker: { color: 'rgba(54, 162, 235, 0.6)' }
        };
        
        const trace2 = {
            x: chartData.labels,
            y: chartData.datasets[1].data,
            name: 'Team Messages',
            type: 'bar',
            marker: { color: 'rgba(75, 192, 192, 0.6)' }
        };
        
        const layout = {
            title: 'Hourly Message Activity',
            xaxis: { title: 'Hour' },
            yaxis: { title: 'Messages' },
            barmode: 'stack',
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#fff' }
        };
        
        Plotly.newPlot('activityChart', [trace1, trace2], layout, {responsive: true});
    }
    
    createSentimentChart(chartData) {
        if (!chartData || !chartData.labels) return;
        
        const trace = {
            labels: chartData.labels,
            values: chartData.data,
            type: 'pie',
            marker: {
                colors: chartData.backgroundColor
            }
        };
        
        const layout = {
            title: 'Sentiment Distribution',
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#fff' }
        };
        
        Plotly.newPlot('sentimentChart', [trace], layout, {responsive: true});
    }
    
    createSentimentTrendChart(chartData) {
        if (!chartData || !chartData.labels) return;
        
        const trace = {
            x: chartData.labels,
            y: chartData.data,
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: 'rgba(75, 192, 192, 1)' },
            marker: { color: 'rgba(75, 192, 192, 0.6)' }
        };
        
        const layout = {
            title: 'Sentiment Trend',
            xaxis: { title: 'Date' },
            yaxis: { title: 'Average Sentiment', range: [-1, 1] },
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#fff' }
        };
        
        Plotly.newPlot('sentimentTrendChart', [trace], layout, {responsive: true});
    }
    
    createCommunicationsChart(clientMessages, teamMessages) {
        const ctx = document.getElementById('communicationsChart');
        if (!ctx) return;
        
        if (this.charts.communications) {
            this.charts.communications.destroy();
        }
        
        this.charts.communications = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Client Messages', 'Team Messages'],
                datasets: [{
                    data: [clientMessages, teamMessages],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(75, 192, 192, 0.6)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(75, 192, 192, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                }
            }
        });
    }
    
    handleTabChange(tabId) {
        // Resize charts when tab becomes visible
        setTimeout(() => {
            if (this.charts.communications) {
                this.charts.communications.resize();
            }
            // Trigger Plotly resize
            const plotlyDivs = ['activityChart', 'sentimentChart', 'sentimentTrendChart'];
            plotlyDivs.forEach(id => {
                const div = document.getElementById(id);
                if (div && div.style.display !== 'none') {
                    Plotly.Plots.resize(div);
                }
            });
        }, 100);
    }
    
    updateLastUpdated(timestamp) {
        const element = document.getElementById('lastUpdated');
        if (element && timestamp) {
            const date = new Date(timestamp);
            element.textContent = date.toLocaleTimeString();
        }
    }
    
    formatTime(seconds) {
        if (!seconds || seconds === null) return 'N/A';
        
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
    
    getPerformanceRating(responseTime) {
        if (!responseTime) return { label: 'N/A', class: 'bg-secondary' };
        
        if (responseTime < 300) { // 5 minutes
            return { label: 'Excellent', class: 'bg-success' };
        } else if (responseTime < 900) { // 15 minutes
            return { label: 'Good', class: 'bg-info' };
        } else if (responseTime < 1800) { // 30 minutes
            return { label: 'Average', class: 'bg-warning' };
        } else {
            return { label: 'Poor', class: 'bg-danger' };
        }
    }
    
    findPeakHour(hourlyData) {
        if (!hourlyData.datasets || !hourlyData.datasets[0]) return 'N/A';
        
        const data = hourlyData.datasets[0].data;
        const maxIndex = data.indexOf(Math.max(...data));
        return hourlyData.labels[maxIndex] || 'N/A';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showLoadingModal() {
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        modal.show();
    }
    
    hideLoadingModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (modal) {
            modal.hide();
        }
    }
    
    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        const modal = new bootstrap.Modal(document.getElementById('errorModal'));
        modal.show();
    }
    
    handleAuthError() {
        localStorage.removeItem('adminToken');
        alert('Authentication failed. Please refresh the page and enter a valid token.');
        location.reload();
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Handle page visibility changes to pause/resume auto-refresh
document.addEventListener('visibilitychange', () => {
    if (window.dashboardManager) {
        if (document.hidden) {
            window.dashboardManager.stopAutoRefresh();
        } else {
            window.dashboardManager.startAutoRefresh();
            window.dashboardManager.loadDashboardData(false);
        }
    }
});
