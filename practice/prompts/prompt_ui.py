from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import streamlit as st

model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    model = model,
    tokenizer = tokenizer,
    max_new_tokens = 100,
    temperature =0.8,
    do_sample= True
)

llm = HuggingFacePipeline(pipeline = pipe)
model = ChatHuggingFace(llm = llm)




st.header('Research tool')
user_input = st.text_input('enter your prompt')

if st.button('Sumarize'):
    result = model.invoke(user_input)
    st.write(result.content)