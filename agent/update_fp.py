import re

# Read file
with open('file_processor.py', 'r') as f:
    content = f.read()

# Replace imports section
old_imports = '''from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import SemanticStrategy
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole'''

new_imports = '''# Import local KB storage instead of AgentCore Memory
from services.local_kb_storage import local_kb_storage'''

content = content.replace(old_imports, new_imports)

# Replace class initialization memory-related code
old_init = '''        # Initialize memory manager for content persistence
        self.memory_manager = MemoryManager(region_name=region)
        self.memory = None'''

new_init = '''        # Use local KB storage instead of AgentCore Memory  
        self.kb_storage = local_kb_storage'''

content = content.replace(old_init, new_init)

# Make memory-related methods no-ops
methods_to_noop = [
    '_start_memory_save_worker',
    '_memory_save_worker',
    '_init_memory',
    '_init_basic_memory', 
    '_save_to_memory',
    '_queue_agent_result_for_memory',
    '_save_chunk_to_memory_sync',
    '_save_agent_result_to_memory'
]

for method in methods_to_noop:
    # Find method and replace with no-op
    pattern = rf'(    def {method}\(self.*?\):)\n(.*?)(?=\n    def |\n    async def |\nclass |\Z)'
    replacement = r'\1\n        """No-op: Replaced by local KB storage."""\n        pass\n'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('file_processor.py', 'w') as f:
    f.write(content)

import logging
logger = logging.getLogger(__name__)
logger.info("Updated file_processor.py successfully")
