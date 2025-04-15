from langchain.llms import LlamaCpp

llm = LlamaCpp(
    model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",  # update path if needed
    temperature=0.7,
    max_tokens=256,
    n_ctx=2048,
    verbose=True
)

question = "What is healthcare compliance and why is it important?"
response = llm(question)

print("\n=== Response ===")
print(response)
