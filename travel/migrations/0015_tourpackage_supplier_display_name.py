# Generated manually for optional per-tour supplier display name

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('travel', '0014_promocode_customers_only_promocode_max_uses_per_user_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tourpackage',
            name='supplier_display_name',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Optional supplier name shown for this tour. Use when entering tours on behalf of another supplier. If blank, the account company name is used.',
                max_length=255,
            ),
        ),
    ]
