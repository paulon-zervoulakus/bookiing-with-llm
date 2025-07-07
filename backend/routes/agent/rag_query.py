import json
import requests
from sentence_transformers import SentenceTransformer
import chromadb
from backend.database import get_collection

def ask_question(
        question: str,
        # persist_directory: str = "./chroma_persist",
        # collection_name: str = "canada",
        top_k: int = 3,
        ollama_url: str = "http://localhost:11434/api/chat",
        model_name: str = "mistral"):
    
    # Load vector store
    # client = chromadb.PersistentClient(path=persist_directory)
    # collection = client.get_collection(name=collection_name)

    # Embed question
    model = SentenceTransformer("all-MiniLM-L6-v2")
    question_embedding = model.encode([question]).tolist()[0]

    # Query ChromaDB
    collection = get_collection()
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k
    )

    relevant_chunks = results["documents"][0]
    pages = results["metadatas"][0]
    context = "\n\n".join(relevant_chunks)

    # print("🔍 Retrieved context from pages:", [p['page'] for p in pages])
    # print("\n📄 Context:\n", context)

    prompt = f"""Use the context below to answer the question.

Context:
{context}

Question:
{question}
"""

    try:
        # Stream the response instead of expecting full JSON at once
        response = requests.post(ollama_url, json={
            "model": model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }, stream=True)

        response.raise_for_status()

        answer_parts = []
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                try:
                    # Each line is a JSON string - parse it
                    chunk = json.loads(decoded_line)
                    # Extract the partial content and append
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        answer_parts.append(content)
                except Exception:
                    # Ignore parse errors, just continue
                    pass

        answer = "".join(answer_parts).strip()
        # print("\n💬 Answer:\n", answer)
        return answer

    except Exception as e:
        print(f"\n⚠️ Error calling Ollama: {e}")
        return context
