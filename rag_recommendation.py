import pandas as pd
import os
import lancedb
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_community.vectorstores import LanceDB 
from langchain_cohere import CohereEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore
import json
import uuid
from typing import List
import streamlit as st

# Initialize Cohere API for embeddings
cohere_api_key = os.getenv("COHERE_API_KEY")
if not cohere_api_key:
    cohere_api_key = input("Enter your Cohere API key: ")
    os.environ["COHERE_API_KEY"] = cohere_api_key

# Initialize Groq API for LLM
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    groq_api_key = input("Enter your Groq API key: ")
    os.environ["GROQ_API_KEY"] = groq_api_key

# Set up Groq LLM
groq_llm = ChatGroq(
    api_key=groq_api_key,
    model_name="meta-llama/llama-4-scout-17b-16e-instruct",
)

try:
    df = pd.read_csv("amazon_scraping_data.csv")
    print(df.head())
except FileNotFoundError:
    raise FileNotFoundError("amazon_scraping_data.csv not found. Please check the file path.")

# Columns you want to embed separately for multi-vector approach
columns_to_embed = ["title", "characteristics", "about_this_item", "technical_details", 
                   "product_description", "additional_information", "compare_with_similar_items", "warranty"]

# Initialize Cohere embeddings
embeddings = CohereEmbeddings(
    cohere_api_key=cohere_api_key,
    model="embed-v4.0"
)

# Initialize LanceDB
db_path = "./PFA/lancedb_data"
db = lancedb.connect(db_path)

# Set up the LanceDB table for multi-vector storage
table_name = "amazon_multi_vector_store"

def create_multi_vector_documents(df: pd.DataFrame) -> tuple:
    """
    Create multiple vector representations for each product.
    Returns parent documents and child documents for multi-vector retrieval.
    """
    parent_documents = []
    child_documents = []
    doc_ids = []
    
    for idx, row in df.iterrows():
        # Create a unique ID for this parent document
        parent_id = str(uuid.uuid4())
        doc_ids.append(parent_id)
        
        # Safely convert values to strings
        def safe_str(value):
            if pd.isna(value):
                return ""
            return str(value).strip()
        
        # Create parent document with full product information
        combined_content = []
        combined_content.append(f"Product: {safe_str(row.get('title', ''))}")
        combined_content.append(f"Price: {safe_str(row.get('price', ''))}")
        combined_content.append(f"Rating: {safe_str(row.get('rating', 'N/A'))}")
        
        # Add all column content
        for col in columns_to_embed:
            content = safe_str(row.get(col, ''))
            if content:
                combined_content.append(f"{col.replace('_', ' ').title()}: {content}")
        
        parent_doc = Document(
            page_content="\n".join(combined_content),
            metadata={
                "id": parent_id,
                "original_index": str(idx),
                "title": safe_str(row.get("title", "")),
                "price": safe_str(row.get("price", "")),
                "rating": safe_str(row.get("rating", "")),
                "url": safe_str(row.get("url", "")),
                "image": safe_str(row.get("image", "")),
                "doc_type": "parent"
            }
        )
        parent_documents.append(parent_doc)
        
        # Create child documents for each important field
        for col in columns_to_embed:
            content = safe_str(row.get(col, ''))
            if content:
                child_doc = Document(
                    page_content=f"{col.replace('_', ' ').title()}: {content}",
                    metadata={
                        "parent_id": parent_id,
                        "original_index": str(idx),
                        "title": safe_str(row.get("title", "")),
                        "price": safe_str(row.get("price", "")),
                        "rating": safe_str(row.get("rating", "")),
                        "url": safe_str(row.get("url", "")),
                        "image": safe_str(row.get("image", "")),
                        "field_type": col,
                        "doc_type": "child"
                    }
                )
                child_documents.append(child_doc)
    
    return parent_documents, child_documents, doc_ids

def create_summaries_for_products(df: pd.DataFrame) -> List[Document]:
    """
    Create AI-generated summaries for each product using the LLM.
    These summaries will be used as additional vectors.
    """
    summary_template = """
    Create a concise summary (2-3 sentences) of this product focusing on its key features, 
    target audience, and main selling points. Be specific and highlight what makes it unique.
    
    Product Information:
    Title: {title}
    Characteristics: {characteristics}
    About: {about}
    Technical Details: {technical}
    Description: {description}
    
    Summary:
    """
    
    prompt = ChatPromptTemplate.from_template(summary_template)
    chain = prompt | groq_llm | StrOutputParser()
    
    summary_documents = []
    
    def safe_str(value):
        if pd.isna(value):
            return ""
        return str(value).strip()
    
    print("Generating AI summaries for products...")
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Creating summaries"):
        try:
            summary = chain.invoke({
                "title": safe_str(row.get("title", "")),
                "characteristics": safe_str(row.get("characteristics", "")),
                "about": safe_str(row.get("about_this_item", "")),
                "technical": safe_str(row.get("technical_details", "")),
                "description": safe_str(row.get("product_description", ""))
            })
            
            # Ensure summary is a clean string
            summary = str(summary).strip()
            
            summary_doc = Document(
                page_content=f"AI Summary: {summary}",
                metadata={
                    "parent_id": str(uuid.uuid4()),  # Add parent_id for consistency
                    "original_index": str(idx),
                    "title": safe_str(row.get("title", "")),
                    "price": safe_str(row.get("price", "")),
                    "rating": safe_str(row.get("rating", "")),
                    "url": safe_str(row.get("url", "")),
                    "image": safe_str(row.get("image", "")),
                    "doc_type": "ai_summary"
                }
            )
            summary_documents.append(summary_doc)
            
        except Exception as e:
            print(f"Error generating summary for product {idx}: {e}")
            # Create a fallback summary
            title = safe_str(row.get('title', 'Unknown'))
            characteristics = safe_str(row.get('characteristics', ''))[:100]
            fallback_summary = f"Product: {title} - {characteristics}"
            
            summary_doc = Document(
                page_content=f"Summary: {fallback_summary}",
                metadata={
                    "parent_id": str(uuid.uuid4()),  # Add parent_id for consistency
                    "original_index": str(idx),
                    "title": safe_str(row.get("title", "")),
                    "price": safe_str(row.get("price", "")),
                    "rating": safe_str(row.get("rating", "")),
                    "url": safe_str(row.get("url", "")),
                    "image": safe_str(row.get("image", "")),
                    "doc_type": "fallback_summary"
                }
            )
            summary_documents.append(summary_doc)
    
    return summary_documents

# Check if table exists
table_exists = table_name in db.table_names()

if not table_exists:
    print(f"Creating new multi-vector LanceDB setup '{table_name}'")
    
    # Create multi-vector documents
    parent_docs, child_docs, doc_ids = create_multi_vector_documents(df)
    
    # Create AI summaries
    summary_docs = create_summaries_for_products(df)
    
    # Combine all documents for embedding
    all_child_docs = child_docs + summary_docs
    
    print(f"Created {len(parent_docs)} parent documents")
    print(f"Created {len(child_docs)} child documents")
    print(f"Created {len(summary_docs)} summary documents")
    
    # Create vector store with all child documents
    print("Creating vector embeddings...")
    batch_size = 50
    vector_store = None
    
    for i in tqdm(range(0, len(all_child_docs), batch_size), desc="Embedding documents"):
        batch = all_child_docs[i:i+batch_size]
        
        try:
            if vector_store is None:
                vector_store = LanceDB.from_documents(
                    documents=batch,
                    embedding=embeddings,
                    connection=db,
                    table_name=table_name
                )
            else:
                vector_store.add_documents(batch)
        except Exception as e:
            print(f"Error processing batch {i//batch_size + 1}: {e}")
    
    # Create document store for parent documents
    docstore = InMemoryStore()
    docstore.mset(list(zip(doc_ids, parent_docs)))
    
    print(f"Multi-vector setup completed!")
    
else:
    print(f"Using existing multi-vector LanceDB table '{table_name}'")
    # Connect to existing table
    vector_store = LanceDB(
        connection=db,
        table_name=table_name,
        embedding=embeddings
    )
    
    # Recreate document store (in production, you'd want to persist this)
    parent_docs, child_docs, doc_ids = create_multi_vector_documents(df)
    docstore = InMemoryStore()
    docstore.mset(list(zip(doc_ids, parent_docs)))

# Create Multi-Vector Retriever
multi_vector_retriever = MultiVectorRetriever(
    vectorstore=vector_store,
    docstore=docstore,
    id_key="parent_id",  # Key to link child docs to parent docs
    search_kwargs={"k": 10}  # Retrieve more child docs initially
)

def ask_question_multi_vector(query_text: str, num_products: int = 3):
    """
    Ask a question using multi-vector retrieval approach.
    """
    # Create a template for the prompt - Fixed to not use {num_products} as a template variable
    template = """
    You are a product recommender system specialist in GAMING GEAR that helps users find the best products based on their preferences.
    
    Use the following pieces of context to answer the question at the end. The context includes multiple perspectives 
    of each product (features, technical details, summaries, etc.).
    
    For each question, suggest the best products with a short description of the product and the reason why 
    the user might like it. Focus on the most relevant aspects based on the user's query.
    
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    
    Context:
    {context}
    
    Question: {question}
    
    Your response:
    """
    
    # Format the retrieved documents into a string
    def format_docs(docs):
        formatted = []
        for doc in docs:
            formatted.append(f"Product: {doc.metadata.get('title', 'Unknown')}")
            formatted.append(f"Price: {doc.metadata.get('price', 'N/A')}")
            formatted.append(f"Rating: {doc.metadata.get('rating', 'N/A')}")
            formatted.append(f"Content: {doc.page_content}")
            formatted.append("-" * 50)
        return "\n".join(formatted)
    
    # Create the prompt
    prompt = ChatPromptTemplate.from_template(template)
    
    # Create the LangChain Expression Language (LCEL) chain
    chain = (
        {"context": multi_vector_retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | groq_llm
        | StrOutputParser()
    )
    
    # Execute the chain
    print(f"\nGenerating multi-vector recommendation for: {query_text}")
    
    # First retrieve documents to display later
    retrieved_docs = multi_vector_retriever.invoke(query_text)
    
    # Run the chain - now only passing the query_text since num_products is not a template variable
    response = chain.invoke(query_text)
    
    # Print the result
    print("\nMulti-Vector Recommendation:")
    print(response)
    
    # Print sources used (unique products only)
    print("\nSources used:")
    seen_titles = set()
    source_count = 0
    
    for doc in retrieved_docs:
        title = doc.metadata.get('title', 'Unknown')
        if title not in seen_titles and source_count < num_products:
            seen_titles.add(title)
            source_count += 1
            print(f"\nProduct {source_count}: {title}")
            print(f"Price: {doc.metadata.get('price', 'N/A')}")
            print(f"Rating: {doc.metadata.get('rating', 'N/A')}")
            print(f"URL: {doc.metadata.get('url', 'N/A')}")
            print(f"Image: {doc.metadata.get('image', 'N/A')}")
            print(f"Content Preview: {doc.page_content[:150]}...")
    
    return {"answer": response, "context": retrieved_docs}


st.set_page_config(page_title=" Product Recommender", layout="wide")

st.title(" AI-Powered Product Recommender for Gaming Gear")

st.markdown("""
Welcome!  Enter your preferences or question, and we'll suggest the best gaming products based on features, specs, and AI analysis.
""")

# Text input for the user's query
query = st.text_input(" What are you looking for?", placeholder="e.g. best wireless gaming mouse under 500 MAD")

# Slider to control number of sources to show
num_sources = st.slider(" Number of products to display", min_value=1, max_value=10, value=3)

# Submit button
if st.button("Find Products"):
    if not query:
        st.warning("Please enter a product-related question or preference.")
    else:
        with st.spinner(" Thinking..."):
            result = ask_question_multi_vector(query_text=query, num_products=num_sources)
        
        st.subheader(" AI Recommendation")
        st.markdown(result["answer"])
        
        st.subheader(" Product Sources Used")
        seen_titles = set()
        source_count = 0
        
        for doc in result["context"]:
            title = doc.metadata.get('title', 'Unknown')
            if title not in seen_titles and source_count < num_sources:
                seen_titles.add(title)
                source_count += 1

                col1, col2 = st.columns([1, 3])
                with col1:
                    image_url = doc.metadata.get('image', '')
                    if image_url and image_url.startswith("http"):
                        st.image(image_url, use_column_width=True)
                    else:
                        st.write(" No Image Available")
                with col2:
                    st.markdown(f"### {title}")
                    st.markdown(f"**Price:** {doc.metadata.get('price', 'N/A')}")
                    st.markdown(f"**Rating:** {doc.metadata.get('rating', 'N/A')}")
                    st.markdown(f"[ View Product]({doc.metadata.get('url', '#')})")
                    st.markdown(f"**Preview:** {doc.page_content[:300]}...")