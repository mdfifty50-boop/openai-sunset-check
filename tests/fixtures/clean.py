from openai import OpenAI

client = OpenAI()
MODEL = "gpt-6-luna"

def answer(q):
    return client.responses.create(model=MODEL, input=q).output_text
