from django import forms

class searchForm(forms.Form):
    skey=forms.CharField(max_length=100, label='search_bar')
    