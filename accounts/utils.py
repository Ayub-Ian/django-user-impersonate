from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.utils import OperationalError
from django.db.utils import ProgrammingError
from django.apps import apps
import random




@deconstructible
class RandomId(object):
    """
    Callable that generates a random primary key that is unique in the specified model's table.
    """

    def __init__(self, model_param):
        """:param: model - can be model name as string or model class"""
        self.model_param = model_param

    def __call__(self):
        random.seed()
        if isinstance(self.model_param, str):
            model_name = self.model_param
            try:
                model_class = apps.get_model(self.model_param)
            except LookupError:
                # the table does not exit
                # this was probably called during a Django migration
                # I'm applying this advice: https://code.djangoproject.com/ticket/24182#comment:2
                model_class = None
        else:
            model_class = self.model_param
            # noinspection PyProtectedMember
            model_name = self.model_param._meta.app_label + '.' + self.model_param._meta.object_name

        scope = 'default'
        if model_name in settings.APPITY_RANDOM_ID:
            scope = model_name
        minimum = settings.APPITY_RANDOM_ID[scope]['MIN']
        maximum = settings.APPITY_RANDOM_ID[scope]['MAX']
        retries = 0
        ModelClass = model_class
        while True:
            rid = random.randint(minimum, maximum)  # nosec B311
            if model_class is None:
                # database table does not exist; we're probably in a migration
                return rid
            try:
                if not ModelClass.objects.filter(id=rid).exists():
                    break
            except (ProgrammingError, OperationalError):
                # db table probably doesn't exist yet
                # workaround for the fact that schema migration (uselessly) tries to get the field's default value
                # ProgrammingError - for mysql
                # OperationalError - for sqlite
                return None
            retries += 1
            if retries >= settings.APPITY_RANDOM_ID[scope]['GROW_AFTER_COLLISIONS']:
                maximum = maximum * settings.APPITY_RANDOM_ID[scope]['GROWTH_FACTOR']
                retries = 0
        return rid
