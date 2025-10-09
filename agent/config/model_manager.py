"""
Model Configuration Manager - Centralized model selection and fallback logic
Handles dynamic model loading, intelligent selection, and automatic fallbacks
"""
import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from .model_config import (
    ModelConfig, ModelSpec, ConfigurationLoader, 
    create_default_config, ModelCapability
)

logger = logging.getLogger(__name__)


class ModelConfigManager:
    """Centralized manager for model configuration and selection."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Determine the correct path based on current working directory
        if config_path is None:
            current_dir = Path.cwd()
            if current_dir.name == "agent":
                self.config_path = "config/default_models.json"
            else:
                self.config_path = "agent/config/default_models.json"
        else:
            self.config_path = config_path
        self.configs: Dict[str, ModelConfig] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load model configurations from file or create defaults."""
        try:
            if Path(self.config_path).exists():
                self.configs = ConfigurationLoader.load_from_file(self.config_path)
                logger.info(f"Loaded model configuration from {self.config_path}")
            else:
                self.configs = create_default_config()
                self.save_config()
                logger.info("Created default model configuration")
            
        except Exception as e:
            logger.error(f"Error loading model configuration: {e}")
            # Fallback to default config
            self.configs = create_default_config()
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            ConfigurationLoader.save_to_file(self.configs, self.config_path)
            logger.info(f"Saved model configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving model configuration: {e}")
    
    def get_model_for_agent(self, agent_type: str, 
                           content_type: Optional[str] = None) -> Optional[ModelSpec]:
        """
        Get the optimal model for an agent based on content type.
        
        Args:
            agent_type: Type of agent (text, pdf, image, video, audio)
            content_type: Optional content type for capability matching
        
        Returns:
            Selected ModelSpec or None if no suitable model found
        """
        if agent_type not in self.configs:
            logger.warning(f"No configuration found for agent type: {agent_type}")
            return None
        
        config = self.configs[agent_type]
        if not config.enabled:
            logger.warning(f"Agent {agent_type} is disabled")
            return None
        
        # Get primary model first
        primary_model = config.primary_model
        
        # Check if primary model supports the content type
        if content_type and not self._model_supports_content_type(primary_model, content_type):
            # Look for a fallback model that supports the content type
            for fallback_model in config.fallback_models:
                if self._model_supports_content_type(fallback_model, content_type):
                    logger.info(f"Selected fallback model {fallback_model.model_id} for {agent_type} agent (content type: {content_type})")
                    return fallback_model
        
        logger.info(f"Selected primary model {primary_model.model_id} for {agent_type} agent")
        return primary_model
    
    def get_fallback_model(self, agent_type: str, 
                          failed_model_id: str,
                          content_type: Optional[str] = None) -> Optional[ModelSpec]:
        """
        Get a fallback model when the primary model fails.
        
        Args:
            agent_type: Type of agent
            failed_model_id: ID of the model that failed
            content_type: Optional content type for capability matching
        
        Returns:
            Fallback ModelSpec or None if no fallback available
        """
        if agent_type not in self.configs:
            return None
        
        config = self.configs[agent_type]
        available_models = config.get_all_models()
        
        # Exclude the failed model
        fallback_models = [m for m in available_models if m.model_id != failed_model_id]
        
        # Filter by capability if needed
        if content_type:
            fallback_models = [
                m for m in fallback_models 
                if self._model_supports_content_type(m, content_type)
            ]
        
        if not fallback_models:
            logger.error(f"No fallback models available for {agent_type}")
            return None
        
        # Select the best fallback (usually the first one in the list)
        fallback_model = fallback_models[0]
        
        logger.info(f"Selected fallback model {fallback_model.model_id} for {agent_type}")
        return fallback_model
    
    def _model_supports_content_type(self, model: ModelSpec, content_type: str) -> bool:
        """Check if a model supports the required content type."""
        content_capability_map = {
            'text': ModelCapability.TEXT,
            'image': ModelCapability.VISION,
            'video': ModelCapability.VISION,
            'audio': ModelCapability.AUDIO,
            'assessment': ModelCapability.ASSESSMENT
        }
        
        required_capability = content_capability_map.get(content_type)
        if not required_capability:
            return True  # If we don't know the content type, assume it's supported
        
        return model.has_capability(required_capability)
    
    def update_model_config(self, agent_type: str, config_updates: Dict[str, Any]) -> bool:
        """
        Update configuration for a specific agent.
        
        Args:
            agent_type: The agent to update
            config_updates: Dictionary of configuration updates
        
        Returns:
            True if update was successful, False otherwise
        """
        try:
            if agent_type not in self.configs:
                logger.error(f"Cannot update unknown agent type: {agent_type}")
                return False
            
            config = self.configs[agent_type]
            
            # Update enabled status
            if 'enabled' in config_updates:
                config.enabled = config_updates['enabled']
            
            # Save updated configuration
            self.save_config()
            
            logger.info(f"Updated configuration for {agent_type} agent")
            return True
            
        except Exception as e:
            logger.error(f"Error updating configuration for {agent_type}: {e}")
            return False


# Global instance
model_config_manager = ModelConfigManager()