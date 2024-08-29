
from .forms import searchForm
def base_data(request):
    return {
        'formSearch': searchForm(),
        'hi': 'hello WOrld',
    }