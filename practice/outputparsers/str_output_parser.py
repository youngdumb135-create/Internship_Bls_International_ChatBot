from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from langchain_core.prompts import PromptTemplate


model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    tokenizer=tokenizer,
    model = model,
    max_new_tokens = 500,
    temperature = 0.8,
    do_sample = True
)

llm = HuggingFacePipeline(pipeline = pipe)
model = ChatHuggingFace(llm =llm)

# 1st prompt -> detailed report
template1 = PromptTemplate(
    template = "Write a detailed report on {topic}",
    input_variables=['topic']
)

# 2nd prompt -> summary
template2 = PromptTemplate(
    template = "Write a 5 line summary on the following text. /n {text}",
    input_variables=['text']
)

prompt1 = template1.invoke({'topic':'black hole'})
result1 = model.invoke(prompt1)
print(result1.content)


prompt2 = template2.invoke({'text':result1.content})
result2 = model.invoke(prompt2)
print(result2.content)