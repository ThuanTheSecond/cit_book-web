from django import forms  
from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError  
from django.contrib.auth import authenticate

# override the user creation form for register
class customUserCreationForm(UserCreationForm): 
    username = forms.CharField(label='username',min_length=5, max_length=150)
    email = forms.CharField(label='email', widget=forms.EmailInput)
    password1 = forms.CharField(label='password1', widget=forms.PasswordInput)        
    password2 = forms.CharField(label='password2', widget=forms.PasswordInput)  
    
    def clean_password2(self):
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']
        if password1 and password2 and password1 != password2:
            # raise forms.ValidationError("Mật khẩu không khớp")
            self.add_error(None, "Mật khẩu không khớp")
        return password2
    
    def clean_email(self):
        email = self.cleaned_data['email']
        user = User.objects.filter(email = email).first()
        if user:
            # raise ValidationError("Email đã bị trùng")
             self.add_error(None, "Email đã bị trùng")
        return email
    
    def clean_username(self):
        username = self.cleaned_data['username']
        user = User.objects.filter(username = username).first()
        if user:
            # raise ValidationError("Email đã bị trùng")
             self.add_error(None, "Username đã bị trùng")
        return username
    
    def save(self, commit = True):  
        user = User.objects.create_user( 
            username = self.cleaned_data['username'],   
            password = self.cleaned_data['password1'],
            email = self.cleaned_data['email'], 
        )  
        return user  
    
    def __init__(self, *args: any, **kwargs: any) -> None:
        super().__init__(*args, **kwargs)
        # errors_messages
        self.fields['username'].error_messages = {
            'required': "Xin hãy nhập vào tên tài khoản",
            'unique': "Tên tài khoản đã bị trùng"
        }
        self.fields['email'].error_messages = {
            'required': "Xin hãy nhập vào email",
            'unique': "Email đã bị trùng"
        }

# override the login form   
class loginForm(forms.Form):
    username = forms.CharField(required=True, min_length=5, max_length=150, label='username')
    password = forms.CharField(required=True, label='password', widget=forms.PasswordInput)
    
    def clean(self):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        user = authenticate(username = username, password = password)
        if not user:
            raise forms.ValidationError('Tên tài khoản hoặc mật khẩu đã sai')
        elif not user.is_active:
           raise forms.ValidationError('Tài khoản đã bị vô hiệu')
        return self.cleaned_data 
    
    def login(self, request):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        user = authenticate(request, username = username, password = password)
        return user