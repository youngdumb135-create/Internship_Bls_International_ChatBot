from langchain_huggingface import HuggingFacePipeline, ChatHuggingFace
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    tokenizer = tokenizer,
    model = model,
    temperature = 0.8,
    do_sample = True
)

llm = HuggingFacePipeline(pipeline = pipe)
model = ChatHuggingFace(llm = llm)

parser = JsonOutputParser()

template = PromptTemplate(
    template = "Give me the name, age and city of a 2 fictional person \n {format_instruction}",
    input_variables= [],
    partial_variables = {'format_instruction' : parser.get_format_instructions()}
)

# prompt  = template.format()
# result = model.invoke(prompt)
# final_result = parser.parse(result.content)

chain = template | model | parser

final_result = chain.invoke({})


print(final_result)
print(type(final_result))