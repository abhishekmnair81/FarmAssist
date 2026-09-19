from langchain_community.vectorstores import FAISS
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.tools import tool
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)

embeddings = None
vector_store = None

def init_vector_store():
    global vector_store, embeddings
    if vector_store is not None:
        return
        
    logger.info("Initializing in-memory FAISS RAG Knowledge Base...")
    try:
        if embeddings is None:
            embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    
        documents = [
            Document(page_content="PM-KISAN (Pradhan Mantri Kisan Samman Nidhi): Provides income support of ₹6,000 per year to all land-holding farmer families in three equal installments of ₹2,000. Recent rules require mandatory e-KYC and Aadhaar seeding with bank accounts."),
            Document(page_content="PMFBY (Pradhan Mantri Fasal Bima Yojana): Provides insurance cover against crop failure due to natural calamities, pests, or diseases. Premium is 2% for Kharif crops, 1.5% for Rabi crops, and 5% for commercial/horticultural crops. Must notify damage within 72 hours via the crop insurance app or toll-free number."),
            Document(page_content="Namo Drone Didi Scheme: Aims to provide agricultural drones to 15,000 Women Self Help Groups (SHGs). Central government provides a subsidy of 80% of the cost of the drone (up to ₹8 Lakhs). Promotes precision spraying of nano-fertilizers like Nano Urea."),
            Document(page_content="PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan): Provides up to 60% subsidy for setting up standalone solar agricultural pumps and solarization of existing grid-connected agriculture pumps. Farmers only pay 10% upfront, with 30% available as bank loans."),
            Document(page_content="Kisan Credit Card (KCC) & Soil Health Card: KCC offers short-term credit for crops at a subsidized 4% interest rate (with prompt repayment). Soil Health Card provides specific recommendations for fertilizer dosages (NPK) based on individual farm soil testing to prevent urea overuse.")
        ]
        
        vector_store = FAISS.from_documents(documents, embeddings)
        logger.info("RAG Knowledge Base initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize RAG Knowledge Base: {e}")

@tool
def query_agri_knowledge_base(query: str) -> str:
    """
    Searches the verified Government Schemes and ICAR Agricultural Knowledge Base.
    Use this tool whenever the user asks about government schemes (PM-KISAN, subsidies, insurance, loans) or standard agricultural practices.
    """
    init_vector_store()
    logger.info(f"Querying RAG for: {query}")
    try:
        results = vector_store.similarity_search(query, k=2)
        if not results:
            return "No information found in the verified knowledge base."
            
        formatted = []
        for doc in results:
            formatted.append(f"{doc.page_content}\n[Source: ICAR Advisory / Govt Scheme Database]")
            
        return "\n\n".join(formatted)
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        return "Failed to access the knowledge base."
