import pandas as pd 
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy import sparse 

class CF(object):
    """docstring for CF"""
    def __init__(self, Y_data, k, dist_func = cosine_similarity, uuCF = 1):
        self.uuCF = uuCF # user-user (1) or item-item (0) CF
        self.Y_data = Y_data if uuCF else Y_data[:, [1, 0, 2]]
        self.k = k # number of neighbor points
        self.dist_func = dist_func
        self.Ybar_data = None
        # number of users and items. Remember to add 1 since id starts from 0
        self.n_users = int(np.max(self.Y_data[:, 0])) + 1 
        self.n_items = int(np.max(self.Y_data[:, 1])) + 1
        
    def add(self, new_data):
        """
        Update Y_data matrix when new ratings come.
        For simplicity, suppose that there is no new user or item.
        """
        self.Y_data = np.concatenate((self.Y_data, new_data), axis = 0)
        
    def normalize_Y(self):
        users = self.Y_data[:, 0] # all users - first col of the Y_data
        self.Ybar_data = self.Y_data.copy()
        self.mu = np.zeros((self.n_users,))
        for n in range(self.n_users):
            # row indices of rating done by user n
            # since indices need to be integers, we need to convert
            ids = np.where(users == n)[0].astype(np.int32)
            # indices of all ratings associated with user n
            item_ids = self.Y_data[ids, 1] 
            # and the corresponding ratings 
            ratings = self.Y_data[ids, 2]
            # take mean
            m = np.mean(ratings) 
            if np.isnan(m):
                m = 0 # to avoid empty array and nan value
            # normalize
            self.Ybar_data[ids, 2] = ratings - self.mu[n]
            
        self.Ybar = sparse.coo_matrix((self.Ybar_data[:, 2],
            (self.Ybar_data[:, 1], self.Ybar_data[:, 0])), (self.n_items, self.n_users))
        self.Ybar = self.Ybar.tocsr()

    def similarity(self):
        self.S = self.dist_func(self.Ybar.T, self.Ybar.T)
        
    def refresh(self):
        """
        Normalize data and calculate similarity matrix again (after
        some few ratings added)
        """
        self.normalize_Y()
        self.similarity() 
        
    def fit(self):
        self.refresh()
        
    def __pred(self, u, i, normalized=1, top_n=None):
        """ 
        predict the rating of user u for item i (normalized)
        Limit the number of top recommendations returned with top_n
        """
        # Step 1: find all users who rated item i
        ids = np.where(self.Y_data[:, 1] == i)[0].astype(np.int32)
        # Step 2: find the users who rated item i
        users_rated_i = (self.Y_data[ids, 0]).astype(np.int32)
        # Step 3: calculate the similarity between user u and users who rated i
        sim = self.S[u, users_rated_i]
        
        # Step 4: Sort the similarities in descending order
        sorted_indices = np.argsort(sim)[-self.k:]  # take top k similarities
        
        # Step 5: If top_n is specified, further limit the number of recommendations
        if top_n is not None:
            sorted_indices = sorted_indices[-top_n:]
        
        # Get corresponding similarities and ratings
        nearest_s = sim[sorted_indices]
        r = self.Ybar[i, users_rated_i[sorted_indices]]
        
        # Step 6: Predict the rating
        if normalized:
            return (r * nearest_s)[0] / (np.abs(nearest_s).sum() + 1e-8)
        
        return (r * nearest_s)[0] / (np.abs(nearest_s).sum() + 1e-8) + self.mu[u]

    def pred(self, u, i, normalized=1, top_n=None):
        """ 
        predict the rating of user u for item i (normalized)
        Limit the number of top recommendations returned with top_n
        """
        if self.uuCF:
            return self.__pred(u, i, normalized, top_n)
        return self.__pred(i, u, normalized, top_n)
    
    
    def recommend(self, u, normalized=1, top_n=None):
        """
        Determine all items should be recommended for user u. (uuCF = 1)
        or all users who might have interest on item u (uuCF = 0).
        """
        ids = np.where(self.Y_data[:, 0] == u)[0]
        items_rated_by_u = self.Y_data[ids, 1].tolist()              
        recommended_items = []
        
        for i in range(self.n_items):
            if i not in items_rated_by_u:
                rating = self.__pred(u, i, normalized)
                if rating > 0:  
                    recommended_items.append((i, rating))  # store item and predicted rating
        
        # Sort by predicted rating in descending order
        recommended_items.sort(key=lambda x: x[1], reverse=True)
        
        # Return only the top_n items if specified
        if top_n is not None:
            return [item[0] for item in recommended_items[:top_n]]
        
        return [item[0] for item in recommended_items]