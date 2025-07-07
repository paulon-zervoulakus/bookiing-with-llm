import chromadb
from pathlib import Path
import fitz
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from requests import Session
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker, Session
# from backend.model.booking import Base
from typing import Generator
from sqlalchemy.ext.declarative import declarative_base

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_persist")

def initialize_chroma_collection():
    """Initialize the ChromaDB collection with PDF data"""
    try:
        # Try to get existing collection
        collection = chroma_client.get_collection(name="canada")
        print("✅ Using existing ChromaDB collection")
        return collection
    except chromadb.errors.NotFoundError:
        print("🔄 Creating new ChromaDB collection...")
        
        # Create new collection
        collection = chroma_client.create_collection(name="canada")
        
        # Load and process PDF
        pdf_path = Path("./data/canada-migration-workbook-national.pdf")
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"❌ PDF file not found: {pdf_path.resolve()}")
        
        print(f"✅ PDF found at: {pdf_path.resolve()}")
        
        # Extract text
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
        )
        
        chunks = text_splitter.split_text(text)
        
        # Create embeddings
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(chunks)
        
        # Add chunks to collection
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            collection.add(
                documents=[chunk],
                embeddings=[embedding.tolist()],
                ids=[f"chunk_{i}"],
            )
        
        print(f"✅ Added {len(chunks)} chunks to ChromaDB")
        return collection

# Initialize collection
# collection = initialize_chroma_collection() 

# Global variable to store the collection
collection = None

def get_collection():
    """Get the initialized collection"""
    global collection
    if collection is None:
        collection = initialize_chroma_collection()
    return collection

# Database
DATABASE_URL = "sqlite:///./bookings.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that creates a new SQLAlchemy session for each request
    and closes it when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.model.booking import BookingModel
    from backend.model.user_model import User

    Base.metadata.create_all(bind=engine)