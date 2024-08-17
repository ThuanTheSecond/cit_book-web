from django.db import models
from django.contrib.auth.models import User
import datetime

# Create your models here.
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='imgUsers\\', default='imgUsers\\blankavatar.jpg')  

    