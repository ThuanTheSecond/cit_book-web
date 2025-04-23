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
            "lập", "trình", "các", "để", "trong", "về", "theo",
            "như", "có", "không", "được", "tại", "bởi", "nhà",
            "qua", "bạn", "rất", "làm", "sau", "đến", "việc"
        ]
        
        # Combine với English stopwords
        self.stop_words = list(text.ENGLISH_STOP_WORDS) + self.vietnamese_stop_words
        
        # Cấu hình TF-IDF cho tiếng Việt
        self.tfidf = TfidfVectorizer(
            stop_words=self.stop_words,
            max_features=5000,
            ngram_range=(1, 2),
            token_pattern=r'(?u)\b\w+\b',  # Pattern phù hợp với tiếng Việt
            strip_accents='unicode'  # Xử lý dấu tiếng Việt
        )
        
        self.model_dir = os.path.join(settings.BASE_DIR, 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        
        self._load_data()
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
        from .models import ContentBook, Book  # Import thêm Book model
        
        try:
            # Xóa cache cũ để load lại data mới
            cache_key = 'content_book_df'
            cache.delete(cache_key)
            
            # Load tất cả ContentBook có book active
            contents = ContentBook.objects.select_related('book').filter(
                book__is_active=True
            ).values('book_id', 'content')
            
            if not contents.exists():
                logger.warning("No content books found in database")
                return pd.DataFrame(columns=['book_id', 'content'])
                
            df = pd.DataFrame(contents)
            
            # Log để debug
            logger.info(f"Loaded {len(df)} books into DataFrame")
            logger.info(f"Sample of loaded data:\n{df.head()}")
            logger.info(f"Book IDs in DataFrame: {df['book_id'].tolist()[:5]}...")
            
            # Tiền xử lý
            df['content'] = df['content'].fillna('')
            df['content'] = df['content'].astype(str)
            
            # Lưu vào cache
            cache.set(cache_key, df, timeout=self.CACHE_TIMEOUT)
            
            self.df = df
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise

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
        try:
            self._load_data()
            
            # Tiền xử lý nội dung
            self.df['content'] = self.df['content'].fillna('')
            self.df['content'] = self.df['content'].astype(str)
            
            # Vector hóa với cấu hình mới
            self.tfidf_matrix = self.tfidf.fit_transform(self.df['content'])
            
            # Tính cosine similarity với chunks
            chunk_size = 1000
            n_samples = self.tfidf_matrix.shape[0]
            cosine_sim = np.zeros((n_samples, n_samples))
            
            for i in range(0, n_samples, chunk_size):
                chunk_end = min(i + chunk_size, n_samples)
                chunk = self.tfidf_matrix[i:chunk_end]
                cosine_sim[i:chunk_end] = cosine_similarity(chunk, self.tfidf_matrix)
            
            self.cosine_sim = cosine_sim
            
            # Lưu model
            model_data = {
                'tfidf': self.tfidf,
                'cosine_sim': self.cosine_sim,
                'book_indices': self.df.index.tolist()
            }
            
            with open(os.path.join(self.model_dir, 'content_model.pkl'), 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info("Model trained and saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False

    def get_recommendations(self, book_id, n_recommendations=5):
        """Get recommendations với caching và error handling"""
        from .models import Book  # Move import here
        
        # Kiểm tra và load lại data nếu df chưa được khởi tạo
        if not hasattr(self, 'df') or self.df is None:
            self._load_data()
            
        cache_key = self._get_cache_key(book_id, n_recommendations)
        
        cached_recommendations = cache.get(cache_key)
        if cached_recommendations is not None:
            return Book.objects.filter(book_id__in=cached_recommendations)
        
        try:
            # Kiểm tra xem book_id có tồn tại trong df không
            if book_id not in self.df['book_id'].values:
                logger.warning(f"Book ID {book_id} not found in content data")
                return []
                
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



