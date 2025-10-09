"""
Model Configuration Package
Provides centralized model configuration and management for MyTutor agents
"""

from .model_config import ModelSpec, ModelConfig, ModelCapability, create_default_config
from .model_manager import ModelConfigManager, model_config_manager

__all__ = [
    'ModelSpec',
    'ModelConfig', 
    'ModelCapability',
    'ModelConfigManager',
    'model_config_manager',
    'create_default_config'
]