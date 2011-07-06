from django.db import models

class StepOne(models.Model):
    name = models.CharField(max_length=20)

class StepTwo(models.Model):
    address = models.CharField(max_length=100)

class StepThree(models.Model):
    city = models.CharField(max_length=50)