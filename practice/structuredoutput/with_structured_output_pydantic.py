from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from typing import Annotated, Optional
from pydantic import BaseModel, Field

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

class Review(BaseModel):
    key_themes: list[str] = Field(description='Write down all the key themes discussed in the review in a list')
    summary: str = Field(description='A brief summary of the review')
    sentiment: str = Field(description='Return the sentiment of the review either negative, positive or neutral')
    pros: Optional[list[str]] = Field(description='Write down all the pros inside a list')
    cons: Optional[list[str]] = Field(description='Write dowm all the cons inside a list')

structured_model = model.with_structured_output(Review)

result = structured_model.invoke(""" The hardware is great but the software feels bloated. There are too many pre-installed apps that I can't remove. Also the UI looks outdated compared to other brands. Hoping for a software fix to this""")

print(result.sentiment)