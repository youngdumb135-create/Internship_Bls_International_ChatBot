from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_huggingface import HuggingFacePipeline, ChatHuggingFace
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    tokenizer = tokenizer,
    model = model,
    temperature = 0.5,
    do_sample = True
)

llm = HuggingFacePipeline(pipeline = pipe)
model = ChatHuggingFace(llm = llm)

messages = [
    SystemMessage(content = "You are a helpful assistant"),
    HumanMessage(content = "Tell me about LangChain")
]

result = model.invoke(messages)
messages.append(AIMessage(content = result.content))