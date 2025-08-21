# Sample Semantic Kernel ChatCompletionAgent with Azure Redis Cache
#
# This script demonstrates a chat agent using Semantic Kernel, with chat history stored in Azure Redis Cache.
#
# Requirements:
#   pip install semantic-kernel redis
#   (and Azure OpenAI SDK if using Azure)


import asyncio
import os
import redis
import pickle
from semantic_kernel import Kernel
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[INFO] python-dotenv not installed. If you use a .env file, run: pip install python-dotenv")

# --- CONFIGURATION ---
# Set your Azure Redis connection string and Azure OpenAI details here
REDIS_HOST = os.environ.get("REDIS_HOST", "<your-redis-host>")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6380))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "<your-redis-password>")
REDIS_SSL = True

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "<your-endpoint>")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "<your-key>")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "<your-deployment>")

# --- REDIS HELPER ---
def get_redis_client():
    return redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        ssl=REDIS_SSL,
        decode_responses=False
    )

def save_thread_to_redis(redis_client, thread_id, thread):
    redis_client.set(f"chat_thread:{thread_id}", pickle.dumps(thread))

def load_thread_from_redis(redis_client, thread_id):
    data = redis_client.get(f"chat_thread:{thread_id}")
    if data:
        return pickle.loads(data)
    return None

# --- MAIN CHAT APP ---
async def main():
    # Connect to Redis
    redis_client = get_redis_client()

    # Prompt for session/thread ID
    session_id = input("Enter session ID (or press Enter to generate a new one): ").strip()
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        print(f"[INFO] Generated session ID: {session_id}")
    thread_id = session_id

    # Set up Semantic Kernel and AzureChatCompletion
    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            deployment_name=AZURE_OPENAI_DEPLOYMENT
        )
    )
    agent = ChatCompletionAgent(
        kernel=kernel,
        name="Assistant",
        instructions="You are a helpful assistant. Answer the user's questions."
    )

    # Load or create chat history thread
    thread = load_thread_from_redis(redis_client, thread_id)
    if not thread:
        thread = ChatHistoryAgentThread()

    print(f"Type 'exit' to quit. Using session ID: {thread_id}")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = await agent.get_response(user_input, thread=thread)
        print(f"Assistant: {response}")
        thread = response.thread
        save_thread_to_redis(redis_client, thread_id, thread)

    print("Chat ended.")

if __name__ == "__main__":
    asyncio.run(main())
