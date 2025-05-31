# Customer Service Monitoring System

A comprehensive Telegram bot monitoring system with sentiment analysis and web dashboard for customer service teams.

## Features

- **Silent Telegram Bot Monitoring**: Monitors 20-100 group chats without sending any messages
- **Real-time KPI Calculation**: Calculates response times, unanswered message rates, and activity metrics
- **Sentiment Analysis**: Uses OpenRouter API with Mistral model to analyze message sentiment
- **Interactive Web Dashboard**: Bootstrap-based dashboard with multiple tabs for different metrics
- **Attention Alerts**: Automatically flags chats that need attention based on configurable thresholds
- **Team Performance Tracking**: Monitor individual team member performance and response times
- **Client Analytics**: Track most active clients and communication patterns

## Tech Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **Telegram Bot**: aiogram v3
- **Message Queue**: Redis
- **Sentiment Analysis**: OpenRouter API (Mistral 7B)
- **Frontend**: Bootstrap 5, Plotly.js, Chart.js
- **Background Processing**: APScheduler, asyncio

## Quick Start

### Environment Variables

Set the following environment variables:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:pass@host:port/dbname
ADMIN_TOKEN=your_secure_admin_token

# Optional
REDIS_URL=redis://localhost:6379
OPENROUTER_API_KEY=your_openrouter_api_key
SESSION_SECRET=your_session_secret
