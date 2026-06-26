from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='idempotencyrecord',
            name='idx_idemp_key_user',
        ),
        migrations.AddConstraint(
            model_name='idempotencyrecord',
            constraint=models.UniqueConstraint(
                fields=['key', 'user'],
                name='uq_idemp_key_user',
            ),
        ),
    ]
