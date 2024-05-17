from django.urls import include, path
from .views import (
    RegisterUserView,
    CreateLinkListCreateView,
    LinkDestroyView,
    AuthTokenObtainPairView,
    LinkDetailsView,
    URLListAPIView,
    LinkListView,
    SendTelegramMessageView,
    ChatViewSet,
    GeneralKnock,
    UserFinishInfoAPIList,
    UserFinishInfoAPIDestroy, ReboundTelegramAPIList, ReboundTelegramAPIDestroy
)


urlpatterns = [

    # Регистрация воркера
    path('register/', RegisterUserView.as_view(), name='register_worker'),

    # Авторизация воркера
    path('auth/', AuthTokenObtainPairView.as_view(), name='worker_token'),

    # Создать/Удалить/Показать сайт сделки
    path('create_link/', CreateLinkListCreateView.as_view(), name='create_link'),
    path('delete_link/<int:pk>/', LinkDestroyView.as_view(), name='delete_link'),
    path('link_list/', LinkListView.as_view(), name='create_link_list'),

    # Тех. поддержка
    path('chats/', ChatViewSet.as_view({'post': 'create'}), name='create_chat'),
    path('api/get_new_messages/', ChatViewSet.as_view({'get': 'get_new_messages'}), name='get_new_messages'),

    # Создание url/ссылки
    path('link_details/<slug:slug>/', LinkDetailsView.as_view(), name='link_details'),
    path('url_list/', URLListAPIView.as_view(), name='slug_list'),

    # telegram test
    path('send_telegram/', SendTelegramMessageView.as_view(), name='send_telegram'),    # личный отсутк
    path('general_send_telegram/', GeneralKnock.as_view(), name='general_knock'),       # общий отстук

    # Вывод и отправка данных Юзера
    path('user_info/', UserFinishInfoAPIList.as_view(),),   # для get и post запроса
    path('user_info/<int:pk>/', UserFinishInfoAPIDestroy.as_view()),   # для удаление данных по id

    # Вывод и отправка данных об отстуке
    path('rebound_info/', ReboundTelegramAPIList.as_view(),),   # для get и post запроса
    path('rebound_info/<int:pk>/', ReboundTelegramAPIDestroy.as_view(),)    # для удаление данных по id
]
