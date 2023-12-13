from django.db import models
import uuid

# Create your models here.
class Final(models.Model):
    # id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    id = models.AutoField(primary_key=True)
    city = models.CharField(max_length=255)
    cases = models.IntegerField()
    deaths = models.IntegerField()
    region = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    month = models.IntegerField()
    year = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'final'
