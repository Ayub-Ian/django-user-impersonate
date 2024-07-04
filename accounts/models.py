import pycountry

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from accounts.utils import RandomId

# Create your models here.
def get_default_currency():
    try:
        return Currency.objects.get(is_default=True)
    except (Currency.MultipleObjectsReturned, Currency.DoesNotExist):
        return None


class AppUser(AbstractUser):
    id = models.BigIntegerField(unique=True, default=RandomId('accounts.AppUser'), primary_key=True)
    email_verified = models.BooleanField(default=False)
    email_last_verified_at = models.DateTimeField(blank=True, null=True, default=None)
    email = models.EmailField(unique=True)
    unverified_email = models.EmailField(blank=True, null=True, default=None)
    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    language = models.CharField(max_length=5, blank=True)
    is_superuser = models.BooleanField(default=False,
                                       help_text=('Designates that this user has all '
                                                  'permissions without explicitly assigning them.'),
                                       verbose_name='superuser status')
    mobile_phone_number = models.CharField(max_length=64, null=True, blank=True)
    unregistered = models.BooleanField(
        default=False,
        help_text=_('Designates whether the user is pending invitation and not signed up yet.'),
    )

    class Meta:
        app_label = 'accounts'
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-date_joined']

class ClientStatus:
    active = 'active'
    inactive = 'inactive'
    suspending = 'suspending'
    suspended = 'suspended'
    deleting = 'deleting'

    name_map = {
        active: _('Active'),
        inactive: _('Inactive'),
        suspending: _('Suspending'),
        suspended: _('Suspended'),
        deleting: _('Deleting'),
    }

    choices = [(active, _('Active')),
               (inactive, _('Inactive')),
               (suspended, _('Suspended')),
               (deleting, _('Deleting'))]

    blocking_statuses = [inactive, suspended, deleting]

class CurrencyManager(models.Manager):
    def get_default_or_first(self):
        return self.filter(is_default=True).first() or self.first()


class Currency(models.Model):
    code = models.CharField(max_length=3,
                            primary_key=True,
                            choices=[(i.alpha_3, i.alpha_3) for i in pycountry.currencies])
    rate = models.DecimalField(default=1, max_digits=12, decimal_places=6)
    is_default = models.BooleanField(default=False)

    objects = CurrencyManager()

    class Meta:
        verbose_name_plural = 'currencies'
        app_label = 'accounts'

    def to_dict(self):
        return dict(code=self.code, rate=self.rate, is_default=self.is_default)

    def save(self, *args, **kwargs):
        if self.is_default:
            # NOTE(tomo): Remove any other defaults
            Currency.objects.filter(is_default=True).exclude(code=self.code).update(is_default=False)
        return super(Currency, self).save(*args, **kwargs)

    def __str__(self):
        return self.code

class Client(models.Model):
    id = models.BigIntegerField(unique=True, default=RandomId('accounts.Client'), primary_key=True)
    first_name = models.CharField(max_length=127)
    last_name = models.CharField(max_length=127)
    company = models.CharField(max_length=127, blank=True, null=True)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=127)
    country = models.CharField(max_length=2, db_index=True, choices=[(country.alpha_2, country.name)
                                                                     for country in pycountry.countries])
    state = models.CharField(max_length=127, blank=True, null=True)
    zip_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=64)
    fax = models.CharField(max_length=64, blank=True, null=True)
    date_created = models.DateTimeField(db_index=True, auto_now_add=True)
    currency = models.ForeignKey(Currency, default=get_default_currency, on_delete=models.CASCADE)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='clients', through='UserToClient')
    status = models.CharField(max_length=16, choices=ClientStatus.choices, db_index=True, default=ClientStatus.inactive)
    suspend_reason = models.CharField(max_length=16, db_index=True, default=None, null=True, blank=True)

    class Meta:
        app_label = 'accounts'
        ordering = ['-date_created']


class UserToClient(models.Model):
    """
    Map user accounts to Client objects and store permissions

    Also stores (email) communications and notifications settings.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    # roles = models.ManyToManyField('accounts.Role', related_name='users', blank=True)
    invitation = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'client')
        app_label = 'accounts'
