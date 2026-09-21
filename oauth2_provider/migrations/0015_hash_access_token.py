import hashlib

import oauth2_provider.models
from django.db import migrations
from django.db.models import F, Value
from django.db.models.functions import Concat
from oauth2_provider.settings import oauth2_settings


def hash_existing_tokens(apps, schema_editor):
    """
    Replace every stored plaintext access token with its SHA-256 digest.

    Existing ``token_checksum`` values already hold the SHA-256 hex digest
    of the plaintext token, so they are reused directly; rows without a
    checksum are hashed from their plaintext value. Existing bearer tokens
    remain valid because lookups hash the presented token in the same way.
    The reverse direction cannot restore the digests to their unknown
    plaintext values and is therefore a no-op.
    """
    AccessToken = apps.get_model(oauth2_settings.ACCESS_TOKEN_MODEL)
    if "token_checksum" not in {field.name for field in AccessToken._meta.get_fields()}:
        # The (possibly swapped) model state at this point has no checksum
        # column, so there is no plaintext data left to migrate.
        return
    AccessToken._default_manager.exclude(token_checksum="").update(
        token=Concat(Value("sha256$"), F("token_checksum"))
    )
    for accesstoken in AccessToken._default_manager.filter(token_checksum="").iterator():
        accesstoken.token = "sha256$" + hashlib.sha256(accesstoken.token.encode("utf-8")).hexdigest()
        accesstoken.save(update_fields=["token"])


class Migration(migrations.Migration):
    dependencies = [
        ("oauth2_provider", "0014_alter_help_text"),
        migrations.swappable_dependency(oauth2_settings.ACCESS_TOKEN_MODEL),
    ]

    operations = [
        migrations.RunPython(hash_existing_tokens, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="accesstoken",
            name="token_checksum",
        ),
        migrations.AlterField(
            model_name="accesstoken",
            name="token",
            field=oauth2_provider.models.HashedTokenField(max_length=71, unique=True),
        ),
    ]
