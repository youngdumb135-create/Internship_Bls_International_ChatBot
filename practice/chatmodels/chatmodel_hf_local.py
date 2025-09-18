import torch
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=100,
    temperature=0.3,
    do_sample=True  # 'temperature' requires 'do_sample' to be True
)


llm = HuggingFacePipeline(pipeline=pipe)

model= ChatHuggingFace(llm = llm)

result = model.invoke("What is the capital of india")

print(result.content)