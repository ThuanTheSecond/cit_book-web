from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction import text
import pandas as pd
import numpy as np
import pickle
import os
from django.conf import settings
from django.core.cache import cache
from functools import lru_cache
import threading
import logging

logger = logging.getLogger(__name__)

class ContentBasedRecommender:

    _instance = None
    _lock = threading.Lock()
    CACHE_KEY_PREFIX = 'book_recommendations:'
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
    def __new__(cls):
        # Singleton pattern để tránh load model nhiều lần
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.vietnamese_stop_words = [
            "và", "là", "của", "những", "với", "từ", "một", "được", 
            "khi", "đã", "cho", "vì", "ở", "này", "giáo", "trình", 
            "lập", "trình", "các", "để", "trong", "về"
        ]
        self.stop_words = list(text.ENGLISH_STOP_WORDS) + self.vietnamese_stop_words
        
        self.tfidf = TfidfVectorizer(
            stop_words=self.stop_words,
            max_features=5000,
            ngram_range=(1, 2)
        )
        
        self.model_dir = os.path.join(settings.BASE_DIR, 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Pre-load model khi khởi tạo
        self._load_model()
        self._initialized = True

    def _get_cache_key(self, book_id, n_recommendations):
        return f"{self.CACHE_KEY_PREFIX}{book_id}:{n_recommendations}"

    @lru_cache(maxsize=1000)
    def _compute_similarity_scores(self, idx):
        """Cache tính toán similarity scores cho mỗi book index"""
        return self.cosine_sim[idx]

    def _load_data(self):
        """Load và tiền xử lý dữ liệu với caching"""
        from .models import ContentBook  # Move import here
        
        cache_key = 'content_book_df'
        df = cache.get(cache_key)
        
        if df is None:
            contents = ContentBook.objects.all().values('book_id', 'content')
            df = pd.DataFrame(contents)
            df['content'] = df['content'].fillna('')
            df['content'] = df['content'].astype(str)
            
            cache.set(cache_key, df, timeout=self.CACHE_TIMEOUT)
        
        self.df = df
        return df

    def _save_model(self):
        """Lưu model với compression"""
        model_data = {
            'tfidf': self.tfidf,
            'cosine_sim': self.cosine_sim,
            'book_indices': self.df['book_id'].tolist()
        }
        
        with open(os.path.join(self.model_dir, 'content_model.pkl'), 'wb') as f:
            pickle.dump(model_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        logger.info("Model saved successfully")

    def _load_model(self):
        """Load model với error handling"""
        try:
            model_path = os.path.join(self.model_dir, 'content_model.pkl')
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    
                self.tfidf = model_data['tfidf']
                self.cosine_sim = model_data['cosine_sim']
                self.book_indices = model_data['book_indices']
                return True
            
            logger.info("No existing model found, training new model")
            return self.train_model()
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return self.train_model()

    def train_model(self):
        """Train model với optimizations"""
        try:
            df = self._load_data()
            
            # Sử dụng parallel processing cho TF-IDF
            self.tfidf_matrix = self.tfidf.fit_transform(df['content'])
            
            # Tính cosine similarity với chunks để tiết kiệm memory
            chunk_size = 1000
            n_samples = self.tfidf_matrix.shape[0]
            cosine_sim = np.zeros((n_samples, n_samples))
            
            for i in range(0, n_samples, chunk_size):
                chunk_end = min(i + chunk_size, n_samples)
                chunk = self.tfidf_matrix[i:chunk_end]
                cosine_sim[i:chunk_end] = cosine_similarity(chunk, self.tfidf_matrix)
            
            self.cosine_sim = cosine_sim
            self._save_model()
            
            # Clear cache khi train model mới
            cache.delete('content_book_df')
            self._compute_similarity_scores.cache_clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False

    def get_recommendations(self, book_id, n_recommendations=5):
        """Get recommendations với caching và error handling"""
        from .models import Book  # Move import here
        
        cache_key = self._get_cache_key(book_id, n_recommendations)
        
        cached_recommendations = cache.get(cache_key)
        if cached_recommendations is not None:
            return Book.objects.filter(book_id__in=cached_recommendations)
        
        try:
            idx = self.df[self.df['book_id'] == book_id].index[0]
            sim_scores = self._compute_similarity_scores(idx)
            similar_indices = np.argsort(sim_scores)[-n_recommendations-1:][::-1][1:]
            recommended_books = self.df['book_id'].iloc[similar_indices].tolist()
            
            cache.set(cache_key, recommended_books, timeout=self.CACHE_TIMEOUT)
            
            return Book.objects.filter(book_id__in=recommended_books)
            
        except Exception as e:
            logger.error(f"Error getting recommendations for book {book_id}: {str(e)}")
            return []

    def update_recommendations(self):
        """Update model với cache invalidation"""
        try:
            success = self.train_model()
            if success:
                # Clear all recommendation caches
                cache.delete_pattern(f"{self.CACHE_KEY_PREFIX}*")
                logger.info("Recommendations updated successfully")
            return success
        except Exception as e:
            logger.error(f"Error updating recommendations: {str(e)}")
            return False
