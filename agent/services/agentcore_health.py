"""
AgentCore Health and Startup Service
Handles health checking, startup validation, and service management for AgentCore runtime
"""
import asyncio
import json
import logging
import os
import subprocess
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import httpx
import psutil

logger = logging.getLogger(__name__)


class AgentCoreHealthService:
    """Service for managing AgentCore runtime health and startup."""
    
    def __init__(self, agent_url: str = "http://localhost:8080", startup_timeout: int = 30):
        self.agent_url = agent_url
        self.startup_timeout = startup_timeout
        self.health_check_interval = 60  # seconds
        self.retry_attempts = 3
        self.retry_delay = 2  # seconds
        
        # Parse URL components
        from urllib.parse import urlparse
        parsed = urlparse(agent_url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 8080
    
    async def check_runtime_health(self) -> Dict[str, Any]:
        """
        Comprehensive health check for AgentCore runtime.
        
        Returns:
            Dict containing health status, details, and recommendations
        """
        health_status = {
            "overall_status": "unknown",
            "timestamp": time.time(),
            "checks": {
                "process_running": False,
                "port_accessible": False,
                "health_endpoint": False,
                "configuration_valid": False
            },
            "details": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Check if AgentCore process is running
            process_check = await self._check_agentcore_process()
            health_status["checks"]["process_running"] = process_check["running"]
            health_status["details"]["process"] = process_check
            
            if not process_check["running"]:
                health_status["issues"].append("AgentCore runtime process is not running")
                health_status["recommendations"].append("Start AgentCore runtime service")
            
            # Check if port is accessible
            port_check = await self._check_port_accessibility()
            health_status["checks"]["port_accessible"] = port_check["accessible"]
            health_status["details"]["port"] = port_check
            
            if not port_check["accessible"]:
                health_status["issues"].append(f"Port {self.port} is not accessible")
                health_status["recommendations"].append(f"Check if port {self.port} is available and not blocked by firewall")
            
            # Check health endpoint if port is accessible
            if port_check["accessible"]:
                endpoint_check = await self._check_health_endpoint()
                health_status["checks"]["health_endpoint"] = endpoint_check["responding"]
                health_status["details"]["endpoint"] = endpoint_check
                
                if not endpoint_check["responding"]:
                    health_status["issues"].append("AgentCore health endpoint is not responding properly")
                    health_status["recommendations"].append("Restart AgentCore runtime or check service configuration")
            
            # Check configuration
            config_check = await self._validate_configuration()
            health_status["checks"]["configuration_valid"] = config_check["valid"]
            health_status["details"]["configuration"] = config_check
            
            if not config_check["valid"]:
                health_status["issues"].extend(config_check.get("issues", []))
                health_status["recommendations"].extend(config_check.get("recommendations", []))
            
            # Determine overall status
            if all(health_status["checks"].values()):
                health_status["overall_status"] = "healthy"
            elif health_status["checks"]["process_running"] and health_status["checks"]["port_accessible"]:
                health_status["overall_status"] = "degraded"
            else:
                health_status["overall_status"] = "critical"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            health_status["overall_status"] = "error"
            health_status["issues"].append(f"Health check failed: {str(e)}")
            return health_status
    
    async def _check_agentcore_process(self) -> Dict[str, Any]:
        """Check if AgentCore process is running."""
        try:
            # Look for processes that might be AgentCore
            agentcore_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
                try:
                    proc_info = proc.info
                    cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                    
                    # Look for AgentCore-related processes
                    if any(keyword in cmdline.lower() for keyword in ['agentcore', 'bedrock-agent', 'strands']):
                        agentcore_processes.append({
                            "pid": proc_info['pid'],
                            "name": proc_info['name'],
                            "cmdline": cmdline,
                            "status": proc_info['status']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "running": len(agentcore_processes) > 0,
                "processes": agentcore_processes,
                "process_count": len(agentcore_processes)
            }
            
        except Exception as e:
            logger.error(f"Error checking AgentCore process: {e}")
            return {
                "running": False,
                "error": str(e),
                "processes": [],
                "process_count": 0
            }
    
    async def _check_port_accessibility(self) -> Dict[str, Any]:
        """Check if the AgentCore port is accessible."""
        try:
            # Try to connect to the port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            
            return {
                "accessible": True,
                "host": self.host,
                "port": self.port,
                "response_time": "< 5s"
            }
            
        except asyncio.TimeoutError:
            return {
                "accessible": False,
                "host": self.host,
                "port": self.port,
                "error": "Connection timeout"
            }
        except ConnectionRefusedError:
            return {
                "accessible": False,
                "host": self.host,
                "port": self.port,
                "error": "Connection refused - service not running"
            }
        except Exception as e:
            return {
                "accessible": False,
                "host": self.host,
                "port": self.port,
                "error": str(e)
            }
    
    async def _check_health_endpoint(self) -> Dict[str, Any]:
        """Check if AgentCore health endpoint is responding."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try multiple common health endpoints
                endpoints_to_try = [
                    "/health",
                    "/status", 
                    "/ping",
                    "/invocations"  # The endpoint we know exists
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        response = await client.get(f"{self.agent_url}{endpoint}")
                        
                        return {
                            "responding": True,
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else "unknown",
                            "content_type": response.headers.get("content-type", "unknown")
                        }
                        
                    except httpx.HTTPStatusError as e:
                        # Even 404 means the server is responding
                        if e.response.status_code == 404:
                            return {
                                "responding": True,
                                "endpoint": endpoint,
                                "status_code": e.response.status_code,
                                "note": "Server responding but endpoint not found"
                            }
                        continue
                    except Exception:
                        continue
                
                return {
                    "responding": False,
                    "error": "No endpoints responded",
                    "endpoints_tried": endpoints_to_try
                }
                
        except Exception as e:
            return {
                "responding": False,
                "error": str(e)
            }
    
    async def _validate_configuration(self) -> Dict[str, Any]:
        """Validate AgentCore configuration."""
        try:
            issues = []
            recommendations = []
            
            # Check environment variables
            required_env_vars = [
                "AWS_REGION",
                "AWS_ACCESS_KEY_ID", 
                "AWS_SECRET_ACCESS_KEY"
            ]
            
            missing_env_vars = []
            for var in required_env_vars:
                if not os.getenv(var):
                    missing_env_vars.append(var)
            
            if missing_env_vars:
                issues.append(f"Missing required environment variables: {', '.join(missing_env_vars)}")
                recommendations.append("Set required AWS environment variables for Bedrock access")
            
            # Check if agent directory exists and has required files
            agent_dir = Path("agent")
            if not agent_dir.exists():
                issues.append("Agent directory not found")
                recommendations.append("Ensure agent directory exists with required agent files")
            else:
                # Check for key agent files
                required_files = [
                    "agents/pdf_agent.py",
                    "agents/video_agent.py", 
                    "file_processor.py"
                ]
                
                missing_files = []
                for file_path in required_files:
                    if not (agent_dir / file_path).exists():
                        missing_files.append(file_path)
                
                if missing_files:
                    issues.append(f"Missing required agent files: {', '.join(missing_files)}")
                    recommendations.append("Ensure all required agent files are present")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "recommendations": recommendations,
                "environment_variables": {
                    var: "set" if os.getenv(var) else "missing" 
                    for var in required_env_vars
                }
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "issues": [f"Configuration validation failed: {str(e)}"],
                "recommendations": ["Check system configuration and permissions"]
            }
    
    async def start_runtime_if_needed(self) -> Dict[str, Any]:
        """
        Attempt to start AgentCore runtime if it's not running.
        
        Returns:
            Dict with startup status and details
        """
        try:
            # First check if it's already running
            health = await self.check_runtime_health()
            
            if health["overall_status"] == "healthy":
                return {
                    "status": "already_running",
                    "message": "AgentCore runtime is already healthy",
                    "health": health
                }
            
            # Try to start the runtime
            startup_result = await self._attempt_startup()
            
            if startup_result["success"]:
                # Wait for startup and verify
                await asyncio.sleep(5)  # Give it time to start
                
                # Verify it's now running
                post_startup_health = await self.check_runtime_health()
                
                return {
                    "status": "started",
                    "message": "AgentCore runtime started successfully",
                    "startup_details": startup_result,
                    "health": post_startup_health
                }
            else:
                return {
                    "status": "failed",
                    "message": "Failed to start AgentCore runtime",
                    "startup_details": startup_result,
                    "health": health
                }
                
        except Exception as e:
            logger.error(f"Error starting AgentCore runtime: {e}")
            return {
                "status": "error",
                "message": f"Error during startup: {str(e)}",
                "error": str(e)
            }
    
    async def _attempt_startup(self) -> Dict[str, Any]:
        """Attempt to start AgentCore runtime using various methods."""
        try:
            # Method 1: Try to start using bedrock-agentcore command
            startup_commands = [
                ["bedrock-agentcore", "start"],
                ["python", "-m", "bedrock_agentcore"],
                ["python3", "-m", "bedrock_agentcore"],
            ]
            
            for cmd in startup_commands:
                try:
                    logger.info(f"Attempting to start AgentCore with command: {' '.join(cmd)}")
                    
                    # Try to run the command
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd="agent"  # Run from agent directory
                    )
                    
                    # Wait a bit to see if it starts successfully
                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(), 
                            timeout=10.0
                        )
                        
                        return {
                            "success": process.returncode == 0,
                            "command": ' '.join(cmd),
                            "returncode": process.returncode,
                            "stdout": stdout.decode() if stdout else "",
                            "stderr": stderr.decode() if stderr else ""
                        }
                        
                    except asyncio.TimeoutError:
                        # Process is still running, which might be good
                        return {
                            "success": True,
                            "command": ' '.join(cmd),
                            "message": "Process started and running in background",
                            "pid": process.pid
                        }
                        
                except FileNotFoundError:
                    logger.info(f"Command not found: {' '.join(cmd)}")
                    continue
                except Exception as e:
                    logger.error(f"Error running command {' '.join(cmd)}: {e}")
                    continue
            
            return {
                "success": False,
                "error": "No suitable startup command found",
                "commands_tried": [' '.join(cmd) for cmd in startup_commands]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_runtime_status(self) -> Dict[str, Any]:
        """Get comprehensive runtime status information."""
        try:
            health = await self.check_runtime_health()
            
            # Add additional status information
            status = {
                "health": health,
                "service_info": {
                    "url": self.agent_url,
                    "host": self.host,
                    "port": self.port,
                    "startup_timeout": self.startup_timeout,
                    "health_check_interval": self.health_check_interval
                },
                "system_info": {
                    "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                    "platform": os.name,
                    "working_directory": str(Path.cwd()),
                    "agent_directory_exists": Path("agent").exists()
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting runtime status: {e}")
            return {
                "error": str(e),
                "health": {"overall_status": "error"}
            }
    
    def validate_configuration(self) -> List[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of configuration issues (empty if valid)
        """
        try:
            # Run synchronous version of configuration validation
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                config_check = loop.run_until_complete(self._validate_configuration())
                return config_check.get("issues", [])
            finally:
                loop.close()
                
        except Exception as e:
            return [f"Configuration validation error: {str(e)}"]


# Global instance
agentcore_health_service = AgentCoreHealthService()