from agent.agent import llm_decide
from browser import use_browser

while True:
    task = input("What should the agent do? ")

    action = llm_decide(task)
    result = use_browser(eval(action))

    print("Page state sent back to LLM")
