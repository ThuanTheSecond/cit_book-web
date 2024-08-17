from django.db import models
import datetime

# Create your models here.
class user(models.Model):
    userid = models.BigAutoField(primary_key= True)
    username = models.CharField(max_length=35, unique= True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=40)
    last_name = models.CharField(max_length=100)
    date_join = models.DateTimeField(default=datetime.datetime.now())
    userImage = models.ImageField(upload_to='imgUsers\\', default='imgUsers\\blankavatar.jpg')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f'{self.userid}, {self.username}, {self.email}, {self.is_active}'
    
    
    
    