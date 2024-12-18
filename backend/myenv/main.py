from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
import motor.motor_asyncio
from bson import ObjectId
import os
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsRegressor
import numpy as np
import asyncio
import re
    

app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "TopSearch")

class Article(BaseModel):
    id: str
    title: str
    summary: str
    published: str
    pdf_link: str
    _id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

# Global dictionary to store the model and vectors for each collection
collection_indices = {}

async def get_database(collection_name: str):
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        await db.command("ping")
        print(f"Successfully connected to MongoDB collection: {collection_name}")
        collection = db[collection_name]
        return collection
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise HTTPException(status_code=500, detail="Error connecting to the database")

async def initialize_knn_index(collection_name: str):
    """
    Initializes the KNN index for the given collection.
    """
    collection = await get_database(collection_name)
    articles = await collection.find().to_list(length=None)
    if not articles:
        return None

    # Prepare the documents for vectorization, with optional values and filtering
    documents = [f"{article.get('title', '')} {article.get('summary', '')}" for article in articles]
    documents = [doc for doc in documents if doc.strip()] #Remove documents that are empty after processing and are only composed of spaces
    if not documents: #If after processing no documents are left, return none to avoid ValueError
        return None

    # Initialize and fit TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(min_df=2) # Set min_df to 2 to ignore terms that appear in less than 2 documents
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    # Initialize and fit KNN model
    knn_model = KNeighborsRegressor(n_neighbors=5, metric='cosine')  # You can adjust k and metric
    knn_model.fit(tfidf_matrix, np.arange(len(documents)))  # Match matrix rows to indices

    # Store the index components
    collection_indices[collection_name] = {
        'vectorizer': vectorizer,
        'knn_model': knn_model,
        'articles': articles,  # Store article data associated with the vectors
        'documents':documents
    }
    
    print(f"KNN index initialized for collection: {collection_name}")


@app.get("/collections/{collection_name}/articles", response_model=List[Article])
async def get_articles(
    collection_name: str,
    year: Optional[int] = Query(None, description="Année de publication (YYYY)"),
    start_year: Optional[int] = Query(None, description="Année de début pour la recherche (YYYY)"),
    end_year: Optional[int] = Query(None, description="Année de fin pour la recherche (YYYY)"),
):
    collection = await get_database(collection_name)
    query = {}

    if year:
        try:
            start_date = datetime(year, 1, 1).isoformat()
            end_date = datetime(year, 12, 31, 23, 59, 59).isoformat()
            query["published"] = {"$gte": start_date, "$lte": end_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid year format")
    elif start_year:
        try:
            start_date = datetime(start_year, 1, 1).isoformat()
            if end_year:
                end_date = datetime(end_year, 12, 31, 23, 59, 59).isoformat()
                query["published"] = {"$gte": start_date, "$lte": end_date}
            else:
                query["published"] = {"$gte": start_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid year format")
    elif end_year:
        try:
                end_date = datetime(end_year, 12, 31, 23, 59, 59).isoformat()
                query["published"] = {"$lte": end_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid year format")

    try:
        if query:
            articles = await collection.find(query).to_list(length=None)
        else:
            articles = await collection.find().to_list(length=None)

        if articles:
            return articles
        else:
                raise HTTPException(status_code=404, detail="Article not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections/{collection_name}", response_model=List[Article])
async def get_all_documents(collection_name: str):
    collection = await get_database(collection_name)
    documents = await collection.find().to_list(length=None)
    for document in documents:
        document["id"] = str(document["_id"])
    return documents

@app.get("/collections/{collection_name}/articles/{article_id}", response_model=Article)
async def get_article_by_id(collection_name:str, article_id: int):
    collection = await get_database(collection_name)
    article = await collection.find_one({"_id": article_id})
    if article:
        return article
    else:
        raise HTTPException(status_code=404, detail="Article not found")


@app.get("/collections/{collection_name}/search", response_model=List[Article])
async def search_articles(
    collection_name: str,
    query_string: Optional[str] = Query(None, description="Terme de recherche"),
):
    if not query_string:
        raise HTTPException(status_code=400, detail="Recherche doit etre un terme valide")

    # Check if the index is already initialized; if not, initialize it.
    if collection_name not in collection_indices:
        await initialize_knn_index(collection_name)
    
    index_data = collection_indices.get(collection_name)

    if not index_data:
        raise HTTPException(status_code=500, detail="KNN index not available")

    vectorizer = index_data['vectorizer']
    knn_model = index_data['knn_model']
    articles = index_data['articles']
    
    # Convert the query string to a vector
    query_vector = vectorizer.transform([query_string])

    # Get the k-nearest neighbors
    distances, indices = knn_model.kneighbors(query_vector)
    
    # Retrieve the corresponding articles
    similar_articles = [articles[idx] for idx in indices.flatten()]

    return similar_articles


# Initialize KNN for all collections upon application startup
@app.on_event("startup")
async def startup_event():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection_names = await db.list_collection_names()
    
    # Initialize KNN index for each collection in parallel
    await asyncio.gather(*[initialize_knn_index(collection_name) for collection_name in collection_names])
    print("All KNN indices initialized")

# Add this function to serve the frontend static files
@app.get("/{full_path:path}")
async def serve_static(full_path: str, request: Request):
    build_dir = Path("./build") # Directory where the frontend's static files are
    # Return the file in the 'build' folder if its is found
    if (build_dir / full_path).exists():
        return FileResponse(build_dir / full_path)
    # If the file is not found, serve the main HTML page
    else:
        return FileResponse(build_dir / 'index.html')