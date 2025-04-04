def get_collection_styles():
    """Return CSS styles for collection display"""
    return """
    <style>
    /* Display case styling */
    .display-case {
        background: linear-gradient(to bottom right, #2c3e50, #1a252f);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), inset 0 0 10px rgba(255, 255, 255, 0.1);
        margin: 20px 0;
    }
    
    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 20px;
        padding: 20px;
    }
    
    .collection-card {
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .collection-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    .card-image-container {
        width: 200px;
        height: 280px;
        overflow: hidden;
        border-radius: 4px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f8f9fa;
        position: relative;
    }
    
    .card-image-container img {
        position: absolute;
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 5px;
    }
    
    .card-details {
        text-align: center;
        width: 100%;
        margin-bottom: 15px;
    }
    
    .card-details h3 {
        font-size: 16px;
        font-weight: bold;
        margin: 5px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .card-details p {
        font-size: 14px;
        color: #666;
        margin: 3px 0;
    }
    
    /* Style Streamlit buttons */
    .stButton > button {
        width: 100%;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 14px;
        transition: all 0.2s;
    }
    
    /* Edit button */
    div[data-testid="column"]:nth-child(1) .stButton > button {
        background-color: #4CAF50;
        color: white;
        border: none;
    }
    
    div[data-testid="column"]:nth-child(1) .stButton > button:hover {
        background-color: #45a049;
    }
    
    /* Delete button */
    div[data-testid="column"]:nth-child(2) .stButton > button {
        background-color: #f44336;
        color: white;
        border: none;
    }
    
    div[data-testid="column"]:nth-child(2) .stButton > button:hover {
        background-color: #da190b;
    }
    
    /* Share button styling */
    .share-button {
        background-color: #4CAF50;
        color: white;
        padding: 8px 16px;
        border-radius: 4px;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin: 10px 0;
        transition: background-color 0.2s;
    }
    
    .share-button:hover {
        background-color: #45a049;
        text-decoration: none;
        color: white;
    }
    
    /* Search filters styling */
    .search-filters {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    /* Mobile adjustments */
    @media (max-width: 640px) {
        .card-grid {
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 10px;
            padding: 10px;
        }
        
        .card-image-container {
            width: 150px;
            height: 210px;
        }
        
        .card-details h3 {
            font-size: 14px;
        }
        
        .card-details p {
            font-size: 12px;
        }
        
        .stButton > button {
            padding: 2px 6px;
            font-size: 12px;
        }
    }
    </style>
    """ 