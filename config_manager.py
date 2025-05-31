import os
import yaml
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manage application configuration from YAML file and environment variables"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self._config = None
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as file:
                    self._config = yaml.safe_load(file)
                logger.info(f"Loaded configuration from {self.config_file}")
            else:
                logger.warning(f"Config file {self.config_file} not found, using defaults")
                self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "agency": {
                "name": "Customer Service Agency",
                "timezone": "UTC"
            },
            "team_members": {},
            "kpi_thresholds": {
                "max_avg_response_time": 3600,  # 1 hour in seconds
                "max_response_time": 7200,      # 2 hours in seconds
                "max_unanswered_percentage": 20,  # 20%
                "max_negative_messages": 5,     # 5 negative messages
                "min_avg_sentiment": -0.3       # Minimum average sentiment score
            },
            "monitoring": {
                "kpi_calculation_interval": 300,  # 5 minutes
                "sentiment_analysis_batch_size": 10,
                "unanswered_timeout_minutes": 60
            },
            "api": {
                "admin_token": os.getenv("ADMIN_TOKEN", "admin-secret-token"),
                "cors_origins": ["*"]
            }
        }
    
    def get_agency_name(self) -> str:
        """Get agency name"""
        return self._config.get("agency", {}).get("name", "Customer Service Agency")
    
    def get_team_members(self) -> Dict[int, Dict]:
        """Get team members configuration"""
        return self._config.get("team_members", {})
    
    def is_team_member(self, user_id: int) -> bool:
        """Check if user ID is a team member"""
        team_members = self.get_team_members()
        return str(user_id) in team_members or user_id in team_members
    
    def get_kpi_thresholds(self) -> Dict:
        """Get KPI thresholds"""
        return self._config.get("kpi_thresholds", {})
    
    def get_monitoring_config(self) -> Dict:
        """Get monitoring configuration"""
        return self._config.get("monitoring", {})
    
    def get_api_config(self) -> Dict:
        """Get API configuration"""
        return self._config.get("api", {})
    
    def update_team_members(self, team_members: Dict):
        """Update team members configuration"""
        try:
            self._config["team_members"] = team_members
            self.save_config()
            logger.info("Updated team members configuration")
        except Exception as e:
            logger.error(f"Error updating team members: {e}")
    
    def update_kpi_thresholds(self, thresholds: Dict):
        """Update KPI thresholds"""
        try:
            self._config["kpi_thresholds"].update(thresholds)
            self.save_config()
            logger.info("Updated KPI thresholds")
        except Exception as e:
            logger.error(f"Error updating KPI thresholds: {e}")
    
    def save_config(self):
        """Save configuration to YAML file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as file:
                yaml.dump(self._config, file, default_flow_style=False, allow_unicode=True)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get_config(self) -> Dict:
        """Get full configuration"""
        return self._config.copy()
    
    def update_config(self, new_config: Dict):
        """Update configuration with new values"""
        try:
            def deep_update(base_dict, update_dict):
                for key, value in update_dict.items():
                    if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                        deep_update(base_dict[key], value)
                    else:
                        base_dict[key] = value
            
            deep_update(self._config, new_config)
            self.save_config()
            logger.info("Updated configuration")
        except Exception as e:
            logger.error(f"Error updating config: {e}")
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get required environment variables"""
        return {
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "DATABASE_URL": os.getenv("DATABASE_URL", ""),
            "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
            "ADMIN_TOKEN": os.getenv("ADMIN_TOKEN", "admin-secret-token"),
            "SESSION_SECRET": os.getenv("SESSION_SECRET", "dev-secret-key")
        }
    
    def validate_configuration(self) -> Dict[str, List[str]]:
        """Validate configuration and return any issues"""
        issues = {"errors": [], "warnings": []}
        
        # Check required environment variables
        env_vars = self.get_environment_variables()
        
        if not env_vars["TELEGRAM_BOT_TOKEN"]:
            issues["errors"].append("TELEGRAM_BOT_TOKEN environment variable is required")
        
        if not env_vars["DATABASE_URL"]:
            issues["errors"].append("DATABASE_URL environment variable is required")
        
        if not env_vars["OPENROUTER_API_KEY"]:
            issues["warnings"].append("OPENROUTER_API_KEY not set, sentiment analysis will be disabled")
        
        # Check KPI thresholds
        thresholds = self.get_kpi_thresholds()
        if thresholds.get("max_avg_response_time", 0) <= 0:
            issues["warnings"].append("max_avg_response_time should be positive")
        
        if thresholds.get("max_unanswered_percentage", 0) < 0 or thresholds.get("max_unanswered_percentage", 0) > 100:
            issues["warnings"].append("max_unanswered_percentage should be between 0 and 100")
        
        # Check team members
        team_members = self.get_team_members()
        if not team_members:
            issues["warnings"].append("No team members configured, all users will be treated as clients")
        
        return issues


# Global config instance
config_manager = ConfigManager()
