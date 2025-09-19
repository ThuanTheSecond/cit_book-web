import numpy as np
import pandas as pd
import os
import pickle
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
from surprise.accuracy import rmse, mae
from surprise import dump
from surprise import KNNWithMeans  # thêm import
from home.models import Rating, Book
from django.contrib.auth.models import User
from .utils import update_recommendation_model
import logging

logger = logging.getLogger(__name__)

@shared_task(
    name='home.tasks.finetune_svd_model_task'
)
def finetune_svd_model_task():
    """
    Fine-tune the SVD model with new ratings data.
    Includes data preprocessing, model training, and evaluation.
    """
    try:
        logger.info("Starting fine-tuning task...")
        
        # Check if enough new ratings
        ratings = Rating.objects.all().select_related('user', 'book')
        ratings_count = ratings.count()
        logger.info(f"Found {ratings_count} ratings in the database")
        
        if ratings_count < 5:
            logger.info(f"Not enough ratings for fine-tuning (found {ratings_count}, need minimum 5)")
            return False
        
        # Log some ratings data for debugging
        sample_ratings = list(ratings[:5].values('user__id', 'book__book_id', 'rating', 'created_at'))
        logger.info(f"Sample ratings: {sample_ratings}")
        
        # Ensure required directories exist
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        models_dir = os.path.join(settings.BASE_DIR, 'models')
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(models_dir, exist_ok=True)
        print(f"Data directory: {data_dir}")
        print(f"Models directory: {models_dir}")
        
        # Prepare fine-tune data
        finetune_path = os.path.join(data_dir, 'finetune_data.csv')
        data = []
        for rating in ratings:
            try:
                entry = {
                    'user_id': str(rating.user.id),
                    'book_id': str(rating.book.book_id),
                    'rating': rating.rating,
                    'timestamp': rating.created_at.timestamp() if rating.created_at else None
                }
                data.append(entry)
            except AttributeError as e:
                logger.error(f"Error processing rating {rating.id}: {e}")
                continue
        
        if not data:
            logger.error("No valid rating data to process")
            raise ValueError("No valid rating data found")
        
        df_finetune = pd.DataFrame(data)
        logger.info(f"Fine-tune DataFrame created with {len(df_finetune)} rows")
        logger.info(f"Fine-tune data sample:\n{df_finetune.head().to_string()}")
        
        df_finetune.to_csv(finetune_path, index=False)
        logger.info(f"Fine-tune data saved to {finetune_path}")
        
        # Load and validate pretrain data
        pretrain_path = os.path.join(data_dir, 'PretrainData_clean.csv')
        if not os.path.exists(pretrain_path):
            logger.error(f"Pretrain data not found at {pretrain_path}")
            raise FileNotFoundError(f"Missing pretrain data: {pretrain_path}")
            
        df_pretrain = pd.read_csv(pretrain_path)
        logger.info(f"Pretrain data loaded: {len(df_pretrain)} rows")
        logger.info(f"Pretrain data sample:\n{df_pretrain.head().to_string()}")
        
        # Calculate global mean
        pretrain_raw_path = os.path.join(data_dir, 'AmazonRating_clean.csv')
        if not os.path.exists(pretrain_raw_path):
            logger.error(f"Raw pretrain data not found at {pretrain_raw_path}")
            raise FileNotFoundError(f"Missing raw pretrain data: {pretrain_raw_path}")
            
        global_mean = pd.read_csv(pretrain_raw_path)['rating'].mean()
        logger.info(f"Global mean rating calculated: {global_mean:.2f}")
        
        # Standardize fine-tune data
        user_counts = df_finetune.groupby('user_id').size().rename('user_count')
        user_means = df_finetune.groupby('user_id')['rating'].mean().rename('user_mean')
        df_finetune = df_finetune.join(user_counts, on='user_id').join(user_means, on='user_id')
        df_finetune['user_mean'] = df_finetune['user_mean'].where(
            df_finetune['user_count'] >= 3, 
            global_mean
        )
        df_finetune['rating_normalized'] = df_finetune['rating'] - df_finetune['user_mean']
        df_finetune_std = df_finetune[['user_id', 'book_id', 'rating_normalized']].rename(
            columns={'rating_normalized': 'rating'}
        )
        logger.info(f"Standardized fine-tune data:\n{df_finetune_std.head().to_string()}")
        
        # Save standardized data
        std_data_path = os.path.join(data_dir, 'finetune_data_std.csv')
        df_finetune_std.to_csv(std_data_path, index=False)
        logger.info(f"Standardized fine-tune data saved to {std_data_path}")
        
        # Combine data
        df_combined = pd.concat([df_pretrain, df_finetune_std], ignore_index=True)
        logger.info(f"Combined data prepared: {len(df_combined)} rows")
        
        # Prepare data for Surprise
        reader = Reader(rating_scale=(-4, 4))
        data = Dataset.load_from_df(df_combined[['user_id', 'book_id', 'rating']], reader)
        
        # Load existing model
        model_path = os.path.join(models_dir, 'finetuned_svd_model.pkl')
        
        if not os.path.exists(model_path):
            model_path = os.path.join(models_dir, 'pretrain_svd_model.pkl')  # đổi tên file theo pretrain
            print(model_path)
            if not os.path.exists(model_path):
                logger.error("No base model found for fine-tuning")
                raise FileNotFoundError("Missing both finetuned and pretrain models")
        
        try:
            with open(model_path, 'rb') as f:
                loaded_data = pickle.load(f)  # Sử dụng pickle.load thay vì surprise.dump.load
            if isinstance(loaded_data, dict) and 'model' in loaded_data:
                model_info = loaded_data
                model = model_info['model']
                logger.info(f"Đã tải mô hình từ từ điển tại {model_path}")
            else:
                # Nếu là đối tượng SVD (file cũ), sử dụng trực tiếp
                model = loaded_data
                # Tạo model_info để đồng bộ định dạng
                model_info = {
                    'model': model,
                    'metrics': {}
                }
            logger.info(f"Đã tải trực tiếp đối tượng SVD từ {model_path} (định dạng cũ)")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

        # Fine-tune model
        model.lr_all = 0.001
        model.n_epochs = 10
        trainset, testset = train_test_split(data, test_size=0.2, random_state=42)
        model.fit(trainset)
        logger.info("Model fine-tuning completed")
        
        # Evaluate model
        predictions = model.test(testset)
        rmse_score = rmse(predictions, verbose=False)
        mae_score = mae(predictions, verbose=False)
        logger.info(f"Model evaluation - RMSE: {rmse_score:.4f}, MAE: {mae_score:.4f}")
        
        # Save fine-tuned model
        output_model_path = os.path.join(models_dir, 'finetuned_svd_model.pkl')
        with open(output_model_path, 'wb') as f:
            pickle.dump(model, f)  # Sử dụng pickle.dump để lưu model
        logger.info(f"Fine-tuned model saved to {output_model_path}")
        
        return {
            'status': 'success',
            'metrics': {
                'rmse': float(rmse_score),
                'mae': float(mae_score)
            },
            'data_processed': len(df_combined)
        }
        
    except Exception as exc:
        logger.error(f"Error in fine-tuning task: {exc}", exc_info=True)
        raise 


@shared_task
def update_content_recommendations_task():
    """Async task để update recommendations"""
    try:
        success = update_recommendation_model()
        if success:
            logger.info("Content recommendations updated successfully")
        else:
            logger.error("Failed to update content recommendations")
        return success
    except Exception as e:
        logger.error(f"Error in update_content_recommendations_task: {str(e)}")
        return False


@shared_task(name='home.tasks.prepare_user_knn_datasets_task')
def prepare_user_knn_datasets_task(_=None):
    """
    Build KNN datasets:
      - knn_finetune_data.csv: ratings from DB (1-5), no normalization
      - knn_pretrain_data.csv: ratings from AmazonRating_clean.csv (1-5), rename user column to 'user_id'
      - userknn_train_data.csv: combined data for debug/training
    """
    try:
        logger.info("Preparing KNN datasets...")

        data_dir = os.path.join(settings.BASE_DIR, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Paths
        pretrain_raw_path = os.path.join(data_dir, 'AmazonRating_clean.csv')
        pretrain_knn_path = os.path.join(data_dir, 'knn_pretrain_data.csv')
        finetune_knn_path = os.path.join(data_dir, 'knn_finetune_data.csv')
        combined_path = os.path.join(data_dir, 'userknn_train_data.csv')

        # 1) Build knn_pretrain_data.csv from AmazonRating_clean.csv
        if not os.path.exists(pretrain_raw_path):
            raise FileNotFoundError(f"Missing raw pretrain data: {pretrain_raw_path}")

        df_pre = pd.read_csv(pretrain_raw_path)

        # Normalize column names: amazon_user_id -> user_id
        if 'amazon_user_id' in df_pre.columns and 'user_id' not in df_pre.columns:
            df_pre = df_pre.rename(columns={'amazon_user_id': 'user_id'})

        expected_cols = {'user_id', 'book_id', 'rating'}
        missing = expected_cols - set(df_pre.columns)
        if missing:
            raise ValueError(f"AmazonRating_clean.csv missing columns: {missing}")

        # Ensure correct dtypes and valid rating range
        df_pre = df_pre[['user_id', 'book_id', 'rating']].astype({'user_id': str, 'book_id': str})
        df_pre = df_pre[(df_pre['rating'] >= 1) & (df_pre['rating'] <= 5)]
        df_pre.to_csv(pretrain_knn_path, index=False)
        logger.info(f"Saved knn_pretrain_data.csv: {len(df_pre)} rows -> {pretrain_knn_path}")

        # 2) Build knn_finetune_data.csv from DB ratings
        ratings = Rating.objects.all().select_related('user', 'book')
        ft_rows = []
        for r in ratings:
            try:
                ft_rows.append({
                    'user_id': str(r.user.id),
                    'book_id': str(r.book.book_id),
                    'rating': float(r.rating),
                    'timestamp': r.created_at.timestamp() if getattr(r, 'created_at', None) else None
                })
            except Exception as e:
                logger.warning(f"Skip rating {getattr(r, 'id', None)}: {e}")

        df_ft = pd.DataFrame(ft_rows, columns=['user_id', 'book_id', 'rating', 'timestamp'])
        if not df_ft.empty:
            df_ft = df_ft[(df_ft['rating'] >= 1) & (df_ft['rating'] <= 5)]
            # Drop timestamp for training if not needed, but keep in file for reference
            df_ft.to_csv(finetune_knn_path, index=False)
            logger.info(f"Saved knn_finetune_data.csv: {len(df_ft)} rows -> {finetune_knn_path}")
        else:
            # still create an empty file with headers for consistency
            pd.DataFrame(columns=['user_id', 'book_id', 'rating', 'timestamp']).to_csv(finetune_knn_path, index=False)
            logger.info("No DB ratings found; created empty knn_finetune_data.csv")

        # 3) Combined debug/training dataset
        df_ft_trim = df_ft[['user_id', 'book_id', 'rating']] if not df_ft.empty else pd.DataFrame(columns=['user_id', 'book_id', 'rating'])
        df_all = pd.concat([df_pre[['user_id', 'book_id', 'rating']], df_ft_trim], ignore_index=True)
        # Keep latest duplicate (prefer DB rows that appear later)
        df_all.drop_duplicates(subset=['user_id', 'book_id'], keep='last', inplace=True)
        df_all.to_csv(combined_path, index=False)
        logger.info(f"Saved combined KNN train data: {len(df_all)} rows -> {combined_path}")

        return {
            'status': 'success',
            'pretrain_rows': int(len(df_pre)),
            'finetune_rows': int(len(df_ft)),
            'combined_rows': int(len(df_all)),
            'files': {
                'pretrain': pretrain_knn_path,
                'finetune': finetune_knn_path,
                'combined': combined_path,
            }
        }
    except Exception as exc:
        logger.error(f"Error preparing KNN datasets: {exc}", exc_info=True)
        raise


@shared_task(name='home.tasks.train_user_knn_cf_task')
def train_user_knn_cf_task(_=None):
    """
    Train user-based CF (KNNWithMeans) using 1-5 ratings.
    Rebuilds dataset from prebuilt KNN CSVs (if available) + current DB ratings.
    """
    try:
        logger.info("Starting user-kNN CF training...")

        data_dir = os.path.join(settings.BASE_DIR, 'data')
        models_dir = os.path.join(settings.BASE_DIR, 'models')
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(models_dir, exist_ok=True)

        pretrain_knn_path = os.path.join(data_dir, 'knn_pretrain_data.csv')
        combined_dump_path = os.path.join(data_dir, 'userknn_train_data.csv')
        pretrain_raw_path = os.path.join(data_dir, 'AmazonRating_clean.csv')

        # 1) Load pretrain (prefer prebuilt KNN CSV)
        if os.path.exists(pretrain_knn_path):
            df_pre = pd.read_csv(pretrain_knn_path)
            logger.info(f"Loaded knn_pretrain_data.csv: {len(df_pre)} rows")
        else:
            if not os.path.exists(pretrain_raw_path):
                logger.error(f"Raw pretrain data not found at {pretrain_raw_path}")
                raise FileNotFoundError(f"Missing raw pretrain data: {pretrain_raw_path}")
            df_pre = pd.read_csv(pretrain_raw_path)
            if 'amazon_user_id' in df_pre.columns and 'user_id' not in df_pre.columns:
                df_pre = df_pre.rename(columns={'amazon_user_id': 'user_id'})
            expected_cols = {'user_id', 'book_id', 'rating'}
            missing = expected_cols - set(df_pre.columns)
            if missing:
                raise ValueError(f"AmazonRating_clean.csv missing columns: {missing}")
            df_pre = df_pre[['user_id', 'book_id', 'rating']].astype({'user_id': str, 'book_id': str})
            df_pre = df_pre[(df_pre['rating'] >= 1) & (df_pre['rating'] <= 5)]
            logger.info(f"Pretrain rows (from raw): {len(df_pre)}")

        # 2) Load current DB ratings (1-5)
        ratings = Rating.objects.all().select_related('user', 'book')
        data = []
        for r in ratings:
            try:
                data.append({
                    'user_id': str(r.user.id),
                    'book_id': str(r.book.book_id),
                    'rating': float(r.rating),
                })
            except Exception as e:
                logger.warning(f"Skip rating {getattr(r,'id',None)}: {e}")
        df_ft = pd.DataFrame(data, columns=['user_id', 'book_id', 'rating'])
        if not df_ft.empty:
            df_ft = df_ft[(df_ft['rating'] >= 1) & (df_ft['rating'] <= 5)]
        logger.info(f"Finetune(DB) rows: {len(df_ft)}")

        # 3) Combine
        df_all = pd.concat([df_pre[['user_id', 'book_id', 'rating']], df_ft], ignore_index=True)
        df_all.drop_duplicates(subset=['user_id', 'book_id'], keep='last', inplace=True)
        logger.info(f"Combined rows: {len(df_all)}")

        # Dump combined (debug)
        df_all.to_csv(combined_dump_path, index=False)
        logger.info(f"Dumped combined train data to {combined_dump_path}")

        # 4) Build Surprise dataset with 1-5 scale
        reader = Reader(rating_scale=(1, 5))
        dataset = Dataset.load_from_df(df_all[['user_id', 'book_id', 'rating']], reader)

        # 5) Train user-based KNNWithMeans
        sim_options = {
            'name': 'pearson_baseline',
            'user_based': True,
            'min_support': 2,
        }
        algo = KNNWithMeans(k=50, min_k=3, sim_options=sim_options)

        trainset, testset = train_test_split(dataset, test_size=0.2, random_state=42)
        algo.fit(trainset)

        # 6) Evaluate
        preds = algo.test(testset)
        rmse_score = rmse(preds, verbose=False)
        mae_score = mae(preds, verbose=False)
        logger.info(f"User-KNN CF - RMSE: {rmse_score:.4f}, MAE: {mae_score:.4f}")

        # 7) Save model
        model_path = os.path.join(models_dir, 'userknn_cf_model.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(algo, f)
        logger.info(f"Saved user-kNN CF model to {model_path}")

        return {
            'status': 'success',
            'metrics': {'rmse': float(rmse_score), 'mae': float(mae_score)},
            'rows': int(len(df_all)),
            'model_path': model_path,
            'data_dump': combined_dump_path
        }

    except Exception as exc:
        logger.error(f"Error training user-kNN CF: {exc}", exc_info=True)
        raise
    
@shared_task(name='home.tasks.update_knn_models_chain')
def update_knn_models_chain():
    from celery import chain
    chain(
        prepare_user_knn_datasets_task.s(),
        train_user_knn_cf_task.s()
    ).delay()