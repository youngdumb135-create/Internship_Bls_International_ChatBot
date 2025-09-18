from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

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

llm = HuggingFacePipeline(pipeline = pipe)
model = ChatHuggingFace(llm = llm)

# 1st prompt
template1 = PromptTemplate(
    template = "Write a detailed report on {topic}",
    input_variables = ['topic']
)

# 2nd prompt
template2 = PromptTemplate(
    template = "Write a 3 line summary on /n {text}",
    input_variables = ['text']
)

parser = StrOutputParser()

chain = template1 | model | parser | template2 | model | parser

result = chain.invoke({'topic':'black hole'})
print(result)