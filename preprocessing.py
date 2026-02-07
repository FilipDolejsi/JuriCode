import os
import dotenv
import argparse
import pymupdf
from openai import OpenAI
import supabase 
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables
dotenv.load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase_client = supabase.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def generate_and_insert_chunks(args): 
    doc = pymupdf.open(args.pdf_path)
    pdf_text = ""
    for page in doc:
        pdf_text += page.get_text() + "\n"

    # Chunk the text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, 
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    texts = text_splitter.split_text(pdf_text)

    print(f"Total chunks created: {len(texts)}")

    for idx, chunk in enumerate(texts):
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=chunk
        )
        
        embedding_vector = response.data[0].embedding
        supabase_client.table("JuriCode").insert({
            "chunk_index": idx, 
            "chunk_content": chunk, 
            "chunk_embedding": embedding_vector
        }).execute()

    print("Successfully processed and stored all chunks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk a PDF and store OpenAI embeddings in Supabase")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file")
    args = parser.parse_args()
    generate_and_insert_chunks(args)