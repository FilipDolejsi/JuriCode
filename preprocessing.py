from langchain_text_splitters import RecursiveCharacterTextSplitter
import pymupdf
import openai
import supabase 
import dotenv
import os
import argparse
from google import genai

dotenv.load_dotenv()
client = genai.Client()
supabase =  supabase.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def generate_and_insert_chunks(args): 
    doc = pymupdf.open(args.pdf_path)
    pdf = []
    for page in doc:
        pdf.append(page.get_text())
    pdf_text = "\n".join(pdf)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100,separators=["\n\n", "\n", " ", ""])
    texts = text_splitter.split_text(pdf_text)

    for idx, chunk in enumerate(texts):
        embedding = client.models.embed_content(
            model="gemini-embedding-001",
            contents=chunk
        )
        supabase.table("content_embedding").insert({"chunk_index": idx, "chunk_content": chunk, "embedding": embedding.embeddings[0].values}).execute()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk a PDF and store embeddings in Supabase")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file")
    args = parser.parse_args()
    generate_and_insert_chunks(args)