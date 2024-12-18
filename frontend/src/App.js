import React, { useState } from "react";
import axios from "axios";
import "./App.css"; // Import the global CSS file

const App = () => {
  const [selectedCollection, setSelectedCollection] = useState("");
  const [year, setYear] = useState("");
  const [startYear, setStartYear] = useState("");
  const [endYear, setEndYear] = useState("");
  const [queryString, setQueryString] = useState(""); // Champ pour la recherche par similarité
  const [articles, setArticles] = useState([]);
  const [error, setError] = useState("");
  const collections = ["CSCV", "CsAI", "CsCL", "CsLG", "StatML"];


  // Fonction de recherche par critères (année, plage d'années)
  const handleSearch = async () => {
    if (!selectedCollection) {
      setError("Veuillez sélectionner une collection.");
      return;
    }


    try {
      const params = {};
      // Ajouter uniquement les paramètres si les champs sont remplis
      if (year) params.year = year;
      if (startYear) params.start_year = startYear;
      if (endYear) params.end_year = endYear;


      const response = await axios.get(`/collections/${selectedCollection}/articles`, { params })
      ;
      setArticles(response.data);
      setError("");
    } catch (error) {
      setError("Erreur lors de la récupération des articles.");
      console.error(error);
    }
  };


  // Fonction de recherche par similarité (KNN)
  const handleSimilaritySearch = async () => {
    if (!selectedCollection) {
      setError("Veuillez sélectionner une collection.");
      return;
    }


    if (!queryString) {
      setError("Veuillez entrer un terme de recherche.");
      return;
    }


    try {
      const response = await axios.get(
        `/collections/${selectedCollection}/search`,
        {
          params: { query_string: queryString },
        }
      );
      setArticles(response.data);
      setError("");
    } catch (error) {
      setError("Erreur lors de la recherche par similarité.");
      console.error(error);
    }
  };


  const handleCollectionChange = (event) => {
    const collection = event.target.value;
    setSelectedCollection(collection);


    // Si les champs de date sont vides, charger directement les articles
    if (!year && !startYear && !endYear) {
      handleSearch();
    }
  };


  return (
    <div className="app-container">
       <header className="app-header">
                <h1 className="app-title">TopSearch</h1>
                <p className="app-subtitle"> Find your articles here</p>
            </header>
            <main className="app-main">
             <div className="topsearch-container">
             <h1 className="topsearch-title">TopSearch Articles</h1>
                 <div className="form-section">
                    <label className="form-label">Sélectionner une collection :</label>
                      <div className="radio-group">
                      {collections.map((collection) => (
                        <div key={collection} className="radio-item">
                            <input
                                type="radio"
                                id={collection}
                                name="collection"
                                value={collection}
                                checked={selectedCollection === collection}
                                onChange={handleCollectionChange}
                                className="radio-input"
                            />
                           <label htmlFor={collection} className="radio-label">{collection}</label>
                        </div>
                     ))}
                   <div className="description">
                    <p>cs.AI : Artificial Intelligence.</p>
                    <p>cs.CL : Computation and Language (NLP).</p>
                    <p>cs.CV : Computer Vision and Pattern Recognition.</p>
                    <p>cs.LG : Machine Learning (dans la section informatique).</p>
                    <p>stat.ML : Machine Learning (dans la section statistiques).</p>
</div>

                     </div>
                 </div>
                <div className="form-section">
                    <label className="form-label">Année de publication :</label>
                    <input
                        type="number"
                        value={year}
                        onChange={(e) => setYear(e.target.value)}
                        className="form-input"
                     />
                </div>
                <div className="form-section">
                     <label className="form-label">Année de début :</label>
                         <input
                            type="number"
                            value={startYear}
                            onChange={(e) => setStartYear(e.target.value)}
                             className="form-input"
                         />
                </div>
                <div className="form-section">
                      <label className="form-label">Année de fin :</label>
                         <input
                            type="number"
                            value={endYear}
                             onChange={(e) => setEndYear(e.target.value)}
                             className="form-input"
                        />
                </div>
                <button onClick={handleSearch} className="search-button">Rechercher par critères</button>
        
                <div className="form-section">
                    <label className="form-label">Recherche par similarité :</label>
                    <input
                        type="text"
                        value={queryString}
                         onChange={(e) => setQueryString(e.target.value)}
                         className="form-input"
                     />
                    <button onClick={handleSimilaritySearch} className="search-button">Rechercher par similarité</button>
                </div>
                {error && <p className="error-message">{error}</p>}
                <ul className="articles-list">
                   {articles.map((article) => (
                         <li key={article.id} className="article-item">
                           <h2 className="article-title">{article.title}</h2>
                           <p className="article-summary">{article.summary}</p>
                         </li>
                     ))}
                </ul>
           </div>
        </main>
        <footer className="app-footer">
             <p>© {new Date().getFullYear()} TopSearch. All rights reserved.</p>
         </footer>
    </div>
  );
};

export default App;