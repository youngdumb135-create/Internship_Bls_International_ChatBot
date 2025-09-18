from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_core.prompts import ChatPromptTemplate

model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    tokenizer = tokenizer,
    model = model,
    max_new_tokens = 100,
    temperature = 0.7,
    do_sample = True
)

llm  = HuggingFacePipeline(pipeline = pipe)
model = ChatHuggingFace(llm =llm)

chat_template = ChatPromptTemplate([
    ('system', 'You are a helpful {domain} expert'),
    ('human','Explain in simple terms, what is {topic}')
])

prompt = chat_template.invoke({'domain':'cricket', 'topic':'leg break'})

print(prompt)

result = model.invoke(prompt)
print(result.content)