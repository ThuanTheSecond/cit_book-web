from django import forms

class searchForm(forms.Form):
    SEARCH_CHOICES = [
        ('all', 'All'),
        ('book_title', 'Tựa đề'),
        ('book_author', 'Tác giả'),
        ('book_publish', 'Xuất bản'),
        ('advance','Nâng cao'),
    ]
    query=forms.CharField(max_length=100, label='search_bar')
    search_type = forms.ChoiceField(choices=SEARCH_CHOICES, required=False, label='Search by')
    
class SearchAdvanceForm(forms.Form):
    field_name = forms.ChoiceField(
        choices=[
            ('book_title', 'Tựa đề'),
            ('book_author', 'Tác giả'),
            ('book_publish', 'Xuất bản'),
        ],
        required=True,
        label='Field'
    )
    search_type = forms.ChoiceField(
        choices=[
            ('icontains', 'Có chứa từ'),
            ('not_icontains', 'Không chứa từ'),
            ('iexact', 'Chính xác'),
        ],
        required=True,
        label='Condition'
        
    )
    value = forms.CharField(required=True,label='Value')
    value.widget.attrs['required'] = 'required'
SearchFormset = forms.formset_factory(SearchAdvanceForm, extra=1)
    