from openai import OpenAI

client = OpenAI()

def answer(question: str) -> str:
    resp = client.responses.create(model="o3", input=question)
    return resp.output_text

def speak(text: str, path: str = "out.mp3") -> None:
    audio = client.audio.speech.create(model="tts-1", voice="alloy", input=text)
    audio.write_to_file(path)
