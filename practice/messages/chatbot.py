import torch
from langchain_huggingface import HuggingFacePipeline, ChatHuggingFace
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

modelid = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
model = AutoModelForCausalLM.from_pretrained(modelid)
tokenizer = AutoTokenizer.from_pretrained(modelid)

pipe = pipeline(
    "text-generation",
    model = model,
    tokenizer= tokenizer,
    temperature = 0.7,
    max_new_tokens = 100,
    do_sample = True
)

llm = HuggingFacePipeline(pipeline=pipe)
model = ChatHuggingFace(llm = llm)


chat_history = [
    SystemMessage(content= "")
]


while True:
    user_input = input('You:')
    chat_history.append(HumanMessage(content = user_input))
    if user_input == 'exit':
        break
    else:
        result = model.invoke(chat_history)
        print("AI: ",result.content)
        chat_history.append(AIMessage(content = result.content))

print(chat_history)

    