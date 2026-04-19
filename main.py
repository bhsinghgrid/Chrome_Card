import asyncio
import sys
from agent import run_agent, build_agent

async def main():
    print("=" * 60)
    print("📅 Calendar & Gmail MCP Agent Test Server")
    print("=" * 60)
    print("\nInitializing Agent (connecting to FastMCP on port 8001)...")
    
    try:
        agent = await build_agent()
        print("✅ Agent successfully initialized!\n")
    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        print("Please make sure you have 'uv run python server.py' running first.")
        return

    print("Type your message to the agent (or type 'quit' to exit):")
    print("-" * 60)
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ")
            if user_input.strip().lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            if not user_input.strip():
                continue
                
            print("\n🤖 Agent is thinking...")
            
            # Execute agent
            result = await run_agent(user_input, agent=agent)
            
            # Print steps exactly as they executed
            steps = result.get("steps", [])
            if steps:
                print("\n[🛠️ Operations Executed]")
                for i, step in enumerate(steps, 1):
                    print(f"  {i}. {step.get('tool')}: {step.get('input')}")
            else:
                print("\n[🛠️ No tools were called]")
                
            # Print answer
            print(f"\n[💡 Final Answer]\n{result.get('answer')}")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error during execution: {e}")

if __name__ == "__main__":
    # Ensure stdout handles colors and emojis natively
    import locale
    locale.setlocale(locale.LC_ALL, '')
    
    asyncio.run(main())
