from celery import shared_task
import pandas as pd
import os
from django.conf import settings
from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
from surprise.accuracy import rmse, mae
from surprise import dump
from home.models import Rating, Book
from django.contrib.auth.models import User

@shared_task
def finetune_svd_model_task():
    print("Starting fine-tuning task...")
    
    # Check if enough new ratings
    ratings = Rating.objects.all().select_related('user', 'book')
    if ratings.count() < 5:  # Minimum threshold
        print("Not enough new ratings for fine-tuning.")
        return
    
    # Prepare fine-tune data
    finetune_path = os.path.join(settings.BASE_DIR, 'data', 'finetune_data.csv')
    data = [
        {
            'user_id': str(rating.user.id),
            'book_id': str(rating.book.book_id),
            'rating': rating.rating,
            'timestamp': rating.timestamp
        }
        for rating in ratings
    ]
    df_finetune = pd.DataFrame(data)
    df_finetune.to_csv(finetune_path, index=False)
    print(f"Fine-tune data: {len(df_finetune)} rows")
    
    # Load pretrain data
    pretrain_path = os.path.join(settings.BASE_DIR, 'data', 'PretrainData_clean.csv')
    df_pretrain = pd.read_csv(pretrain_path)
    print(f"Pretrain data: {len(df_pretrain)} rows")
    
    # Calculate global_mean
    pretrain_raw_path = os.path.join(settings.BASE_DIR, 'data', 'AmazonRating_clean.csv')
    global_mean = pd.read_csv(pretrain_raw_path)['rating'].mean()
    print(f"Global mean rating: {global_mean}")
    
    # Standardize fine-tune data
    user_counts = df_finetune.groupby('user_id').size().rename('user_count')
    user_means = df_finetune.groupby('user_id')['rating'].mean().rename('user_mean')
    df_finetune = df_finetune.join(user_counts, on='user_id').join(user_means, on='user_id')
    df_finetune['user_mean'] = df_finetune['user_mean'].where(df_finetune['user_count'] >= 3, global_mean)
    df_finetune['rating_normalized'] = df_finetune['rating'] - df_finetune['user_mean']
    df_finetune_std = df_finetune[['user_id', 'book_id', 'rating_normalized']].rename(columns={'rating_normalized': 'rating'})
    
    # Save standardized data
    df_finetune_std.to_csv(os.path.join(settings.BASE_DIR, 'data', 'finetune_data_std.csv'), index=False)
    
    # Combine data
    df_combined = pd.concat([df_pretrain, df_finetune_std], ignore_index=True)
    print(f"Combined data: {len(df_combined)} rows")
    
    # Prepare data for Surprise
    reader = Reader(rating_scale=(-4, 4))
    data = Dataset.load_from_df(df_combined[['user_id', 'book_id', 'rating']], reader)
    
    # Load model
    model_path = os.path.join(settings.BASE_DIR, 'models', 'finetuned_svd_model.pkl')
    if not os.path.exists(model_path):
        model_path = os.path.join(settings.BASE_DIR, 'models', 'pretrain_svd_model.pkl')
    
    _, model = dump.load(model_path)
    
    # Fine-tune
    model.lr_all = 0.001
    model.n_epochs = 10
    trainset, testset = train_test_split(data, test_size=0.2, random_state=42)
    model.fit(trainset)
    
    # Evaluate
    predictions = model.test(testset)
    rmse_score = rmse(predictions, verbose=True)
    mae_score = mae(predictions, verbose=True)
    
    # Save model
    output_model_path = os.path.join(settings.BASE_DIR, 'models', 'finetuned_svd_model.pkl')
    dump.dump(output_model_path, algo=model)
    print(f"Fine-tuned model saved to {output_model_path}")
    print(f"RMSE: {rmse_score}, MAE: {mae_score}")