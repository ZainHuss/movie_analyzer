import django_tables2 as tables
from .models import Movie

class MovieTable(tables.Table):
    class Meta:
        model = Movie
        template_name = "django_tables2/bootstrap.html"
        fields = ('rank', 'title', 'genre', 'director', 'year', 
                 'runtime', 'rating', 'votes', 'revenue', 'metascore')