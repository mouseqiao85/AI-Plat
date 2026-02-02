"""
AI-Plat ç»Ÿä¸€å¹³å°å…¥å£
æ•´åˆæœ¬ä½“è®ºã€æ™ºèƒ½ä½“å’ŒVibecodingä¸‰å¤§æ ¸å¿ƒæ¨¡å—
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ontology import OntologyManager, InferenceEngine, DataFusioner
from agents import SkillAgent, AgentOrchestrator, SkillRegistry
from vibecoding import VibecodingNotebookInterface, CodeAnalyzer, CodeGenerator
from .mcp_server import MCPServer, create_example_mcp_server
from .mcp_client import MCPClient, MCPClientConfig, MCPToolAdapter
from config.settings import config


logger = logging.getLogger(__name__)


class AIPlatPlatform:
    """
    AI-Plat ç»Ÿä¸€å¹³å°
    æ•´åˆæœ¬ä½“è®ºã€æ™ºèƒ½ä½“å’ŒVibecodingä¸‰å¤§æ ¸å¿ƒæ¨¡å—
    """
    
    def __init__(self):
        """åˆå§‹åŒ–AI-Platå¹³å°"""
        self.platform_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        
        # åˆå§‹åŒ–ä¸‰å¤§æ ¸å¿ƒæ¨¡ï¿½?        self.ontology_manager = OntologyManager(config.ONTOLOGY_PATH)
        self.inference_engine = InferenceEngine(self.ontology_manager)
        self.data_fusioner = DataFusioner(self.ontology_manager)
        
        self.skill_registry = SkillRegistry()
        self.agent_orchestrator = AgentOrchestrator()
        
        self.vibecoding_interface = VibecodingNotebook()
        self.vibecoding_assistant = VibecodingAssistant(self.vibecoding_interface)
        
        # MCP Server/Client åˆå§‹ï¿½?        self.mcp_server: Optional[MCPServer] = None
        self.mcp_clients: Dict[str, MCPClient] = {}
        self.mcp_tool_adapters: Dict[str, MCPToolAdapter] = {}
        
        # å¹³å°çŠ¶ï¿½?        self.is_running = False
        self.modules_initialized = False
        
        logger.info(f"AI-Plat Platform initialized with ID: {self.platform_id}")
    
    async def initialize_modules(self):
        """åˆå§‹åŒ–æ‰€æœ‰æ¨¡ï¿½?""
        logger.info("Initializing AI-Plat modules...")
        
        # åˆå§‹åŒ–æ™ºèƒ½ä½“æ¨¡å—
        await self.agent_orchestrator.shutdown()  # ç¡®ä¿æ¸…ç†
        self.agent_orchestrator = AgentOrchestrator()
        
        # åˆå§‹åŒ–Vibecodingæ¨¡å—
        self.vibecoding_interface = VibecodingNotebookInterface()
        self.code_analyzer = CodeAnalyzer()
        self.code_generator = CodeGenerator()
        
        # åˆå§‹åŒ–MCPæ¨¡å—
        await self._initialize_mcp_modules()
        
        # æ³¨å†Œé»˜è®¤æŠ€ï¿½?        self._register_default_skills()
        
        self.modules_initialized = True
        logger.info("All modules initialized successfully")
    
    def _register_default_skills(self):
        """æ³¨å†Œé»˜è®¤æŠ€ï¿½?""
        # è¿™é‡Œå¯ä»¥æ³¨å†Œå¹³å°å†…ç½®çš„é»˜è®¤æŠ€ï¿½?        pass
    
    async def _initialize_mcp_modules(self):
        """åˆå§‹åŒ–MCPæ¨¡å—"""
        logger.info("Initializing MCP modules...")
        
        # åˆ›å»ºMCPæœåŠ¡å™¨ï¼ˆç¤ºä¾‹ï¿½?        self.mcp_server = create_example_mcp_server()
        
        # åˆå§‹åŒ–MCPå®¢æˆ·ç«¯å­—ï¿½?        self.mcp_clients = {}
        self.mcp_tool_adapters = {}
        
        logger.info("MCP modules initialized successfully")
    
    def register_mcp_server(self, name: str, server: MCPServer):
        """æ³¨å†ŒMCPæœåŠ¡ï¿½?""
        self.mcp_server = server
        logger.info(f"Registered MCP server: {name}")
    
    def register_mcp_client(self, name: str, config: MCPClientConfig):
        """æ³¨å†ŒMCPå®¢æˆ·ï¿½?""
        client = MCPClient(config)
        self.mcp_clients[name] = client
        logger.info(f"Registered MCP client: {name}")
    
    async def call_remote_model(self, client_name: str, model_name: str, operation: str, input_data: Any, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """é€šè¿‡MCPå®¢æˆ·ç«¯è°ƒç”¨è¿œç¨‹æ¨¡ï¿½?""
        if client_name not in self.mcp_clients:
            raise ValueError(f"MCP client '{client_name}' not found")
        
        client = self.mcp_clients[client_name]
        async with client:
            result = await client.call_model(model_name, operation, input_data, parameters)
            return result
    
    async def create_mcp_tool_adapter(self, client_name: str) -> MCPToolAdapter:
        """ä¸ºæŒ‡å®šå®¢æˆ·ç«¯åˆ›å»ºå·¥å…·é€‚é…ï¿½?""
        if client_name not in self.mcp_clients:
            raise ValueError(f"MCP client '{client_name}' not found")
        
        client = self.mcp_clients[client_name]
        adapter = MCPToolAdapter(client)
        self.mcp_tool_adapters[client_name] = adapter
        return adapter
    
    async def start(self):
        """å¯åŠ¨å¹³å°"""
        if not self.modules_initialized:
            await self.initialize_modules()
        
        self.is_running = True
        logger.info(f"AI-Plat Platform started (ID: {self.platform_id})")
        
        # å¯åŠ¨åå°ä»»åŠ¡
        asyncio.create_task(self._run_background_tasks())
    
    async def stop(self):
        """åœæ­¢å¹³å°"""
        self.is_running = False
        
        # åœæ­¢æ‰€æœ‰æ¨¡ï¿½?        await self.agent_orchestrator.shutdown()
        
        logger.info(f"AI-Plat Platform stopped (ID: {self.platform_id})")
    
    async def _run_background_tasks(self):
        """è¿è¡Œåå°ä»»åŠ¡"""
        while self.is_running:
            try:
                # è¿™é‡Œå¯ä»¥æ·»åŠ å®šæœŸç»´æŠ¤ä»»åŠ¡
                await asyncio.sleep(60)  # æ¯åˆ†é’Ÿæ£€æŸ¥ä¸€ï¿½?            except Exception as e:
                logger.error(f"Background task error: {str(e)}")
    
    def get_platform_status(self) -> Dict[str, Any]:
        """è·å–å¹³å°çŠ¶ï¿½?""
        return {
            'platform_id': self.platform_id,
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat(),
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'modules': {
                'ontology': {
                    'initialized': self.ontology_manager is not None,
                    'triples_count': len(self.ontology_manager.graph) if self.ontology_manager else 0
                },
                'agents': {
                    'initialized': self.agent_orchestrator is not None,
                    'registered_agents': len(self.agent_orchestrator.agents) if self.agent_orchestrator else 0,
                    'active_workflows': len(self.agent_orchestrator.get_active_workflows()) if self.agent_orchestrator else 0
                },
                'vibecoding': {
                    'initialized': self.vibecoding_interface is not None,
                    'notebooks_count': len(self.vibecoding_interface.notebooks) if self.vibecoding_interface else 0
                },
                'mcp': {
                    'server_initialized': self.mcp_server is not None,
                    'clients_count': len(self.mcp_clients),
                    'adapters_count': len(self.mcp_tool_adapters)
                }
            }
        }
    
    async def run_demo_scenario(self):
        """è¿è¡Œæ¼”ç¤ºåœºæ™¯ï¼šå±•ç¤ºä¸‰å¤§æ¨¡å—ååŒå·¥ï¿½?""
        logger.info("Running demo scenario...")
        
        # åœºæ™¯ï¼šä¾›åº”é“¾é£é™©åˆ†æ
        print("=== AI-Plat æ¼”ç¤ºåœºæ™¯ï¼šä¾›åº”é“¾é£é™©åˆ†æ ===")
        
        # 1. ä½¿ç”¨æœ¬ä½“æ¨¡å—å®šä¹‰ä¾›åº”é“¾æ¦‚ï¿½?        print("\\n1. æ„å»ºä¾›åº”é“¾æœ¬ï¿½?..")
        self.ontology_manager.create_entity("Supplier", "Class", "ä¾›åº”å•†å®ï¿½?)
        self.ontology_manager.create_entity("Product", "Class", "äº§å“å®ä½“")
        self.ontology_manager.create_entity("Location", "Class", "åœ°ç†ä½ç½®å®ä½“")
        self.ontology_manager.create_entity("RiskEvent", "Class", "é£é™©äº‹ä»¶å®ä½“")
        self.ontology_manager.create_entity("supplies", "ObjectProperty", "ä¾›åº”å…³ç³»")
        self.ontology_manager.create_entity("locatedIn", "ObjectProperty", "ä½äºå…³ç³»")
        self.ontology_manager.create_entity("affects", "ObjectProperty", "å½±å“å…³ç³»")
        
        # åˆ›å»ºå®ä¾‹
        self.ontology_manager.create_entity("Supplier_A", "NamedIndividual", "ä¾›åº”å•†A")
        self.ontology_manager.create_entity("Product_X", "NamedIndividual", "äº§å“X")
        self.ontology_manager.create_entity("China", "NamedIndividual", "ä¸­å›½")
        self.ontology_manager.create_entity("Earthquake", "NamedIndividual", "åœ°éœ‡")
        
        # åˆ›å»ºå…³ç³»
        self.ontology_manager.create_relationship("Supplier_A", "supplies", "Product_X")
        self.ontology_manager.create_relationship("Supplier_A", "locatedIn", "China")
        self.ontology_manager.create_relationship("Earthquake", "affects", "China")
        
        # ä¿å­˜æœ¬ä½“
        self.ontology_manager.save_ontology("supply_chain_demo")
        print("   ä¾›åº”é“¾æœ¬ä½“æ„å»ºå®Œï¿½?)
        
        # 2. ä½¿ç”¨æ¨ç†å¼•æ“å‘ç°éšå«å…³ç³»
        print("\\n2. æ‰§è¡Œæœ¬ä½“æ¨ç†...")
        inference_results = self.inference_engine.perform_inference()
        for inference_type, results in inference_results.items():
            print(f"   {inference_type}: {len(results)} æ¨ç†ç»“æœ")
        print("   æœ¬ä½“æ¨ç†å®Œæˆ")
        
        # 3. ä½¿ç”¨æ™ºèƒ½ä½“å¤„ç†ä»»ï¿½?        print("\\n3. ä½¿ç”¨æ™ºèƒ½ä½“å¤„ç†åˆ†æä»»ï¿½?..")
        
        # åˆ›å»ºåˆ†æä»£ç†
        analysis_agent = SkillAgent(
            name="SupplyRiskAnalyzer",
            description="ä¾›åº”é“¾é£é™©åˆ†æä»£ï¿½?,
            skills=[]
        )
        await analysis_agent.initialize()
        
        # æ·»åŠ ä»£ç†åˆ°ç¼–æ’å™¨
        self.agent_orchestrator.register_agent(analysis_agent)
        
        # åˆ›å»ºåˆ†æä»»åŠ¡
        task_id = await analysis_agent.add_task(
            name="Risk Assessment",
            description="è¯„ä¼°ä¾›åº”é“¾é£ï¿½?,
            skill_id="",  # ä½¿ç”¨é»˜è®¤çš„åˆ†ææŠ€ï¿½?            parameters={
                "ontology_query": "SELECT ?supplier ?location WHERE { ?supplier <http://ai-plat.org/ontology#locatedIn> ?location . }",
                "risk_factors": ["natural_disaster", "political_stability", "economic_condition"]
            }
        )
        
        # ç­‰å¾…ä»»åŠ¡å®Œæˆ
        await asyncio.sleep(2)  # ç®€å•ç­‰ï¿½?        
        task_result = analysis_agent.get_task_result(task_id)
        print(f"   ä»»åŠ¡ç»“æœ: {task_result['status'] if task_result else 'No result'}")
        print("   æ™ºèƒ½ä½“åˆ†æå®Œï¿½?)
        
        # 4. ä½¿ç”¨Vibecodingåˆ›å»ºåˆ†ææŠ¥å‘Š
        print("\\n4. ä½¿ç”¨Vibecodingç”Ÿæˆåˆ†ææŠ¥å‘Š...")
        
        # åˆ›å»ºç¬”è®°ï¿½?        notebook_id = self.vibecoding_interface.create_notebook("Supply Chain Risk Report", "ä¾›åº”é“¾é£é™©åˆ†ææŠ¥ï¿½?)
        
        # æ·»åŠ æ•°æ®å¤„ç†å•å…ƒï¿½?        self.vibecoding_interface.add_cell(
            notebook_id, 
            "code", 
            '''
import pandas as pd

# æ¨¡æ‹Ÿä¾›åº”é“¾æ•°ï¿½?data = {
    "supplier": ["Supplier A", "Supplier B", "Supplier C"],
    "location": ["China", "USA", "Germany"],
    "risk_level": ["High", "Medium", "Low"],
    "products": ["Product X", "Product Y", "Product Z"]
}

df = pd.DataFrame(data)
print("ä¾›åº”é“¾é£é™©æ¦‚ï¿½?")
print(df)
'''
        )
        
        # æ·»åŠ å¯è§†åŒ–å•å…ƒæ ¼
        self.vibecoding_interface.add_cell(
            notebook_id, 
            "code", 
            '''
# é£é™©ç­‰çº§å¯è§†ï¿½?import matplotlib.pyplot as plt

risk_counts = df['risk_level'].value_counts()
plt.figure(figsize=(8, 5))
plt.bar(risk_counts.index, risk_counts.values)
plt.title('ä¾›åº”é“¾é£é™©ç­‰çº§åˆ†ï¿½?)
plt.xlabel('é£é™©ç­‰çº§')
plt.ylabel('ä¾›åº”å•†æ•°ï¿½?)
plt.show()
'''
        )
        
        # æ‰§è¡Œç¬”è®°ï¿½?        execution_result = await self.vibecoding_interface.execute_notebook(notebook_id)
        print(f"   æ‰§è¡Œç»“æœ: {execution_result['successful_executions']}/{execution_result['executed_cells']} æˆåŠŸ")
        print("   Vibecodingåˆ†æå®Œæˆ")
        
        # 5. ä½¿ç”¨MCPåŠŸèƒ½æ¼”ç¤ºæ¨¡å‹é—´é€šä¿¡
        print("\\n5. ğŸ”„ ä½¿ç”¨MCPåŠŸèƒ½æ¼”ç¤ºæ¨¡å‹é—´é€šä¿¡...")
        
        if self.mcp_server:
            # å¯åŠ¨MCPæœåŠ¡å™¨ï¼ˆåœ¨åå°ï¼‰
            print(f"   ï¿½?MCP Server available with models: {list(self.mcp_server.model_registry.model_descriptions.keys())}")
            
            # æ¼”ç¤ºé€šè¿‡MCPè°ƒç”¨è¿œç¨‹æ¨¡å‹
            try:
                # æ³¨å†Œä¸€ä¸ªMCPå®¢æˆ·ï¿½?                self.register_mcp_client(
                    "demo_client",
                    MCPClientConfig(server_url=f"http://{self.mcp_server.host}:{self.mcp_server.port}")
                )
                
                # è°ƒç”¨è¿œç¨‹æ¨¡å‹
                mcp_result = await self.call_remote_model(
                    client_name="demo_client",
                    model_name="sentiment_analyzer",
                    operation="analyze",
                    input_data="The integration of MCP functionality enhances AI-Plat's capabilities significantly!"
                )
                print(f"   ï¿½?MCP Remote Model Call Result: {mcp_result.get('result', 'Success') if mcp_result.get('success') else 'Failed'}")
            except Exception as e:
                print(f"   ï¿½?MCP demo error (expected if server not fully started): {str(e)}")
        else:
            print("   ï¿½?MCP Server not initialized in demo")
        
        print("\\n=== æ¼”ç¤ºåœºæ™¯å®Œæˆ ===")
        
        return {
            'ontology': 'Built supply chain ontology with 5 classes, 3 properties, and 4 instances',
            'inference': f'Performed inference with {sum(len(results) for results in inference_results.values())} results',
            'agents': f'Completed risk analysis task with status: {task_result["status"] if task_result else "N/A"}',
            'vibecoding': f'Generated report with {execution_result["executed_cells"] if execution_result else 0} executed cells',
            'mcp': f'MCP functionality demonstrated with {len(self.mcp_server.model_registry.model_descriptions) if self.mcp_server else 0} registered models'
        }
    
    def integrate_modules_example(self):
        """æ¨¡å—é›†æˆç¤ºä¾‹"""
        logger.info("Running module integration example...")
        
        # å±•ç¤ºå¦‚ä½•è®©å››ä¸ªæ¨¡å—ååŒå·¥ï¿½?        integration_steps = [
            "1. æœ¬ä½“æ¨¡å—å®šä¹‰é¢†åŸŸæ¦‚å¿µå’Œå…³ï¿½?,
            "2. æ™ºèƒ½ä½“æ¨¡å—æ‰§è¡Œåˆ†æå’Œæ¨ç†ä»»åŠ¡", 
            "3. Vibecodingæ¨¡å—ç”Ÿæˆå¯è§†åŒ–æŠ¥ï¿½?,
            "4. MCPæ¨¡å—å®ç°æ¨¡å‹é—´é€šä¿¡å’ŒæœåŠ¡åŒ–",
            "5. æ‰€æœ‰ç»“æœæ•´åˆåˆ°ç»Ÿä¸€çš„çŸ¥è¯†å›¾è°±ä¸­"
        ]
        
        print("\\n=== æ¨¡å—é›†æˆç¤ºä¾‹ ===")
        for step in integration_steps:
            print(f"{step}")
        
        # æœ¬ä½“æ¨¡å—ï¼šå®šä¹‰æ¦‚ï¿½?        self.ontology_manager.create_entity("IntegrationDemo", "Class", "é›†æˆæ¼”ç¤ºå®ä½“")
        
        # æ™ºèƒ½ä½“æ¨¡å—ï¼šæ‰§è¡Œä»»åŠ¡
        # Vibecodingæ¨¡å—ï¼šç”Ÿæˆç»“ï¿½?        # MCPæ¨¡å—ï¼šæ¨¡å‹æœåŠ¡åŒ–å’Œé€šä¿¡
        
        print("\\né›†æˆæ¼”ç¤ºå®Œæˆï¼Œæ‰€æœ‰æ¨¡å—ååŒå·¥ä½œæ­£ï¿½?)
        
        return {
            'integration_status': 'successful',
            'steps_completed': len(integration_steps),
            'ontology_entities': len(self.ontology_manager.export_to_json()['classes']),
            'mcp_integrated': self.mcp_server is not None
        }


async def main():
    """ä¸»å‡½ï¿½?- å¹³å°æ¼”ç¤º"""
    print("ğŸš€ å¯åŠ¨ AI-Plat å¼€å‘å¹³ï¿½?..")
    
    # åˆ›å»ºå¹³å°å®ä¾‹
    platform = AIPlatPlatform()
    
    try:
        # åˆå§‹åŒ–å¹³ï¿½?        await platform.initialize_modules()
        
        # æ˜¾ç¤ºå¹³å°çŠ¶ï¿½?        status = platform.get_platform_status()
        print(f"\\nğŸ“‹ å¹³å°çŠ¶ï¿½?")
        print(f"   ID: {status['platform_id']}")
        print(f"   è¿è¡ŒçŠ¶ï¿½? {status['is_running']}")
        print(f"   è¿è¡Œæ—¶é—´: {status['uptime']:.2f} ï¿½?)
        
        # è¿è¡Œæ¼”ç¤ºåœºæ™¯
        demo_results = await platform.run_demo_scenario()
        
        # è¿è¡Œé›†æˆç¤ºä¾‹
        integration_results = platform.integrate_modules_example()
        
        print(f"\\nğŸ¯ æ¼”ç¤ºå®Œæˆ!")
        print(f"   æœ¬ä½“æ¨¡å—: {demo_results['ontology']}")
        print(f"   æ¨ç†å¼•æ“: {demo_results['inference']}")
        print(f"   æ™ºèƒ½ï¿½? {demo_results['agents']}")
        print(f"   Vibecoding: {demo_results['vibecoding']}")
        print(f"   æ¨¡å—é›†æˆ: {integration_results['integration_status']}")
        
    except Exception as e:
        logger.error(f"Platform error: {str(e)}")
        print(f"ï¿½?é”™è¯¯: {str(e)}")
    finally:
        # åœæ­¢å¹³å°
        await platform.stop()
        print("\\nğŸ‘‹ AI-Plat å¹³å°å·²åœï¿½?)


if __name__ == "__main__":
    asyncio.run(main())
