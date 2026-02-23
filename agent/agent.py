from openai import OpenAI
client = OpenAI()

def llm_decide(task):
    prompt = f"""
    You are a browser agent.
    Convert this task into browser steps in JSON:

    Task: {task}

    Output format:
    {{
      "type": "open/click/type",
      "url": "",
      "selector": "",
      "text": ""
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
