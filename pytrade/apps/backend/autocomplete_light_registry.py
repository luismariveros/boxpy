#encoding=utf8
import autocomplete_light
from pytrade.apps.backend.models import Ubicacion
from django.contrib.auth.models import User

# # This will generate a PersonAutocomplete class
# autocomplete_light.register(Cliente,
#     # Just like in ModelAdmin.search_fields
#     search_fields=['^first_name', 'last_name', 'codigo'],
#     # This will actually html attribute data-placeholder which will set
#     # javascript attribute widget.autocomplete.placeholder.
#     autocomplete_js_attributes={'placeholder': 'Other model name ?',},
# )

autocomplete_light.register(Ubicacion,
                            search_fields=['nombre'])


class UserAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ['first_name', 'last_name', 'cliente__codigo']
    autocomplete_js_attributes = {'placeholder': 'Nombre o Codigo del Cliente?', }

    def choices_for_request(self):
        self.choices = self.choices.filter(is_staff=False)
        return super(UserAutocomplete, self).choices_for_request()


autocomplete_light.register(User,UserAutocomplete)