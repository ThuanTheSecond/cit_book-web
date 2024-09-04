from django import forms

class searchForm(forms.Form):
    SEARCH_CHOICES = [
        ('all', 'All'),
        ('book_title', 'Title'),
        ('book_author', 'Author'),
        ('book_publish', 'Publish'),
        ('absolute','Absolute'),
    ]
    query=forms.CharField(max_length=100, label='search_bar')
    search_type = forms.ChoiceField(choices=SEARCH_CHOICES, required=False, label='Search by')
    