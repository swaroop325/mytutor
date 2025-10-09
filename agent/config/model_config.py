"""
Model Configuration System - Data structures and configuration management
Handles model specifications, capabilities, and configuration loading
"""
import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """Enumeration of model capabilities."""
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    ASSESSMENT = "assessment"





@dataclass
class ModelSpec:
    """Specification for an AI model configuration."""
    model_id: str
    region: str = "us-east-1"
    max_tokens: int = 4096
    temperature: float = 0.1
    capabilities: List[ModelCapability] = field(default_factory=list)
    description: str = ""
    
    def __post_init__(self):
        """Convert string capabilities to ModelCapability enums."""
        if self.capabilities and isinstance(self.capabilities[0], str):
            self.capabilities = [ModelCapability(cap) for cap in self.capabilities]
    
    def has_capability(self, capability: Union[str, ModelCapability]) -> bool:
        """Check if model has a specific capability."""
        if isinstance(capability, str):
            capability = ModelCapability(capability)
        return capability in self.capabilities


@dataclass
class ModelConfig:
    """Configuration for an agent's model usage."""
    agent_type: str
    primary_model: ModelSpec
    fallback_models: List[ModelSpec] = field(default_factory=list)
    enabled: bool = True
    
    def get_all_models(self) -> List[ModelSpec]:
        """Get all models (primary + fallbacks) for this agent."""
        return [self.primary_model] + self.fallback_models
    
    def get_model_by_capability(self, capability: Union[str, ModelCapability]) -> Optional[ModelSpec]:
        """Get the first available model with the specified capability."""
        for model in self.get_all_models():
            if model.has_capability(capability):
                return model
        return None


class ConfigurationLoader:
    """Handles loading and validation of model configurations."""
    
    @staticmethod
    def load_from_file(config_path: Union[str, Path]) -> Dict[str, ModelConfig]:
        """Load model configurations from JSON or YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    raw_config = yaml.safe_load(f)
                else:
                    raw_config = json.load(f)
            
            return ConfigurationLoader._parse_config(raw_config)
            
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            raise
    
    @staticmethod
    def _parse_config(raw_config: Dict[str, Any]) -> Dict[str, ModelConfig]:
        """Parse raw configuration dictionary into ModelConfig objects."""
        configs = {}
        
        for agent_type, agent_config in raw_config.get('agents', {}).items():
            try:
                # Parse primary model
                primary_model_data = agent_config['primary_model']
                primary_model = ModelSpec(**primary_model_data)
                
                # Parse fallback models
                fallback_models = []
                for fallback_data in agent_config.get('fallback_models', []):
                    fallback_models.append(ModelSpec(**fallback_data))
                
                # Create model config
                config = ModelConfig(
                    agent_type=agent_type,
                    primary_model=primary_model,
                    fallback_models=fallback_models,
                    enabled=agent_config.get('enabled', True)
                )
                
                configs[agent_type] = config
                
            except Exception as e:
                logger.error(f"Error parsing configuration for agent {agent_type}: {e}")
                raise
        
        return configs
    
    @staticmethod
    def save_to_file(configs: Dict[str, ModelConfig], config_path: Union[str, Path]) -> None:
        """Save model configurations to JSON or YAML file."""
        config_path = Path(config_path)
        
        # Convert to serializable format
        raw_config = {
            'agents': {}
        }
        
        for agent_type, config in configs.items():
            agent_data = {
                'primary_model': asdict(config.primary_model),
                'fallback_models': [asdict(model) for model in config.fallback_models],
                'enabled': config.enabled
            }
            
            # Convert enums to strings for serialization
            agent_data['primary_model']['capabilities'] = [
                cap.value if isinstance(cap, ModelCapability) else cap 
                for cap in agent_data['primary_model']['capabilities']
            ]
            
            for fallback in agent_data['fallback_models']:
                fallback['capabilities'] = [
                    cap.value if isinstance(cap, ModelCapability) else cap 
                    for cap in fallback['capabilities']
                ]
            
            raw_config['agents'][agent_type] = agent_data
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(raw_config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(raw_config, f, indent=2)
            
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration to {config_path}: {e}")
            raise
    
    @staticmethod
    def validate_config(config: ModelConfig) -> List[str]:
        """Validate a model configuration and return any issues."""
        issues = []
        
        # Validate primary model
        if not config.primary_model.model_id:
            issues.append("Primary model must have a model_id")
        
        if config.primary_model.max_tokens <= 0:
            issues.append("Primary model max_tokens must be positive")
        
        if not (0.0 <= config.primary_model.temperature <= 2.0):
            issues.append("Primary model temperature must be between 0.0 and 2.0")
        
        return issues


def create_default_config() -> Dict[str, ModelConfig]:
    """Create default model configurations for all agent types."""
    
    # Define common models
    claude_haiku = ModelSpec(
        model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
        region="us-east-1",
        max_tokens=4096,
        temperature=0.1,
        capabilities=[ModelCapability.TEXT],
        description="Fast, cost-effective model for text processing"
    )
    
    claude_sonnet = ModelSpec(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        region="us-east-1",
        max_tokens=8192,
        temperature=0.1,
        capabilities=[ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.ASSESSMENT],
        description="High-capability model for complex analysis and vision tasks"
    )
    
    # Create agent configurations
    configs = {
        "text": ModelConfig(
            agent_type="text",
            primary_model=claude_haiku,
            fallback_models=[claude_sonnet]
        ),
        
        "pdf": ModelConfig(
            agent_type="pdf",
            primary_model=claude_sonnet,
            fallback_models=[claude_haiku]
        ),
        
        "image": ModelConfig(
            agent_type="image",
            primary_model=claude_sonnet,
            fallback_models=[claude_haiku]
        ),
        
        "video": ModelConfig(
            agent_type="video",
            primary_model=claude_sonnet,
            fallback_models=[claude_haiku]
        ),
        
        "audio": ModelConfig(
            agent_type="audio",
            primary_model=claude_haiku,
            fallback_models=[claude_sonnet]
        ),
        
        "training": ModelConfig(
            agent_type="training",
            primary_model=claude_sonnet,  # Use Sonnet for complex reasoning tasks
            fallback_models=[claude_haiku]
        )
    }
    
    return configs