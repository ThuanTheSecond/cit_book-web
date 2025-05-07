from django import forms
import json

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
    FIELD_CHOICES = [
        ('book_title', 'Tựa đề'),
        ('book_author', 'Tác giả'),
        ('book_publish', 'Xuất bản'),
    ]
    
    field_name = forms.ChoiceField(
        choices=FIELD_CHOICES,
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
    value = forms.CharField(required=False, label='Value', help_text = "Nhập vào từ khóa")

# Tạo một form riêng cho selected_categories
class CategorySelectionForm(forms.Form):
    selected_categories = forms.CharField(required=False, widget=forms.HiddenInput())
    
    def clean(self):
        cleaned_data = super().clean()
        selected_categories = cleaned_data.get('selected_categories')
        
        # Kiểm tra xem đã chọn thể loại chưa
        has_categories = False
        if selected_categories:
            try:
                category_ids = json.loads(selected_categories)
                if category_ids:  # Nếu có ít nhất một thể loại được chọn
                    has_categories = True
            except (json.JSONDecodeError, TypeError):
                pass
        
        return cleaned_data

# Tạo formset cho SearchAdvanceForm
SearchFormset = forms.formset_factory(SearchAdvanceForm, extra=1)    
