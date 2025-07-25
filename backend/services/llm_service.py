import os
from langchain.llms import OpenAI
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType

class LLMService:
    """Service for managing LangChain LLM agent for query processing."""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.llm = OpenAI(openai_api_key=self.openai_api_key, temperature=0)
        # Placeholder: Add tools as needed for agent
        self.tools = []
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
        )

    def run(self, prompt: str) -> str:
        """Run the agent with a given prompt and return the response."""
        return self.agent.run(prompt)

# Singleton instance for import
llm_service = LLMService() 