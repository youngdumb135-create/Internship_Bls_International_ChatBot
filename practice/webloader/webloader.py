from langchain_community.document_loaders import WebBaseLoader

loader = WebBaseLoader("https://www.blsslovakiavisa.com/")
documents = loader.load()
print(documents[0].page_content)

""" for doc in documents:
    print(doc.page_content)
    print(doc.metadata) """