import hashlib

import oauth2_provider.models
from django.db import migrations
from django.db.models import F, Value
from django.db.models.functions import Concat


def hash_existing_tokens(apps, schema_editor):
    """
    Replace stored plaintext access tokens with their SHA-256 digest,
    mirroring oauth2_provider migration 0015 for the swapped test model.
    """
    SampleAccessToken = apps.get_model("tests", "SampleAccessToken")
    SampleAccessToken._default_manager.exclude(token_checksum="").update(
        token=Concat(Value("sha256$"), F("token_checksum"))
    )
    for accesstoken in SampleAccessToken._default_manager.filter(token_checksum="").iterator():
        accesstoken.token = "sha256$" + hashlib.sha256(accesstoken.token.encode("utf-8")).hexdigest()
        accesstoken.save(update_fields=["token"])


class Migration(migrations.Migration):
    dependencies = [
        ("tests", "0008_sampledevicegrant"),
    ]

    operations = [
        migrations.RunPython(hash_existing_tokens, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="sampleaccesstoken",
            name="token_checksum",
        ),
        migrations.AlterField(
            model_name="sampleaccesstoken",
            name="token",
            field=oauth2_provider.models.HashedTokenField(max_length=71, unique=True),
        ),
    ]
