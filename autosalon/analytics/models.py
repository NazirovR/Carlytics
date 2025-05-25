from django.db import models
from django.contrib.auth.models import User

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=1, choices=[('M', 'Мужской'), ('F', 'Женский')])
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

class Visit(models.Model):
    PURPOSE_CHOICES = [
        ('new_car', 'Осмотр нового автомобиля'),
        ('service', 'Сервис'),
        ('test_drive', 'Тест-драйв'),
        ('documents', 'Документы'),
        ('other', 'Другое'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    time_in = models.DateTimeField()
    time_out = models.DateTimeField()
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)

    def __str__(self):
        return f"Посещение {self.client.name} ({self.purpose})"
