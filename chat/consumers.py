import json

from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer, \
    JsonWebsocketConsumer, AsyncJsonWebsocketConsumer
from channels.consumer import SyncConsumer, AsyncConsumer
from channels.exceptions import StopConsumer
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.auth import login, logout
from django.contrib.auth import get_user_model

from chat.models import Online


class ChatConsumer(WebsocketConsumer):

    def connect(self):
        user = get_user_model().objects.filter(email='admin@mail.com').first()
        async_to_sync(login)(self.scope, user)  # login user
        # async_to_sync(logout)(self.scope)         # logout user
        # После операций с сессиями такими как login, ее необходимо сохранять!
        # self.scope['session'].save()
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        async_to_sync(self.channel_layer.group_add)(self.room_name, self.channel_name)
        self.accept()  # Метод для установки соединения.

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.room_name, self.channel_name)

    def receive(self, text_data=None, bytes_data=None):
        # for h in self.scope['headers']:
        #     print(f'Header {h[0]} >> {h[1]}')
        #     print('*' * 20)
        # print('=' * 20)
        # print(f'URL_ROUTE {self.scope["url_route"]}')
        # print('=' * 20)
        # print(f'PATH {self.scope["path"]}')
        # json_data = json.loads(text_data)
        # message = json_data['message']
        # self.send(text_data=json.dumps({
        #     'message': message
        # }))
        print(self.scope['user'])
        async_to_sync(logout)(self.scope)
        self.scope['session'].save()
        print(self.scope['user'])
        async_to_sync(self.channel_layer.group_send)(
            self.room_name,
            {
                'type': 'chat.message',
                'text': text_data
            }
        )

    def chat_message(self, event):
        self.send(text_data=event['text'])


class AsyncChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # await database_sync_to_async(self.create_online())()  # Если нет декоратора:
        await self.create_online()  # Если есть декоратор:
        user = await self.get_user_from_db()
        await login(self.scope, user)
        await database_sync_to_async(self.scope['session'].save)()
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        await self.channel_layer.group_add(self.room_name,
                                           self.channel_name)
        self.scope['session']['my_var'] = 'hello string'
        await database_sync_to_async(self.scope['session'].save)()
        await self.accept()

    async def disconnect(self, code):
        await self.delete_online()
        await self.channel_layer.group_discard(self.room_name,
                                               self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        print(self.scope['user'])
        await logout(self.scope)
        await database_sync_to_async(self.scope['session'].save)()
        print(self.scope['user'])
        await self.refresh_online()
        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': 'chat.message',
                'text': text_data
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=event['text'])

    @database_sync_to_async
    def create_online(self):
        new, _ = Online.objects.get_or_create(name=self.channel_name)
        self.online = new

    @database_sync_to_async
    def delete_online(self):
        Online.objects.filter(name=self.channel_name).delete()

    @database_sync_to_async
    def refresh_online(self):
        self.online.refresh_from_db()

    @database_sync_to_async
    def get_user_from_db(self):
        return get_user_model().objects.filter(email='admin@mail.com').first()


class BaseSyncConsumer(SyncConsumer):
    # event - dict, первый ключ которого - type, который содержит тип сообщения, с которым хотите работать.
    def websocket_connect(self, event):
        self.send({
            "type": "websocket.accept"
        })

    def websocket_receive(self, event):
        self.send({
            "type": "websocket.send",
            "text": event['text']
        })

    def websocket_disconnect(self):
        raise StopConsumer()


class BaseAsyncConsumer(AsyncConsumer):

    async def websocket_connect(self, event):
        await self.send({
            "type": "websocket.accept"
        })

    async def websocket_receive(self, event):
        await self.send({
            "type": "websocket.send",
            "text": event['text']
        })


class ChatJsonConsumer(JsonWebsocketConsumer):

    def connect(self):
        self.accept()  # Метод для установки соединения.

    def disconnect(self, code):
        pass

    def receive_json(self, content, **kwargs):
        self.send_json(content=content)

    @classmethod
    def encode_json(cls, content):
        return super().encode_json(content)

    @classmethod
    def decode_json(cls, text_data):
        return super().decode_json(text_data)


class ChatAsyncJsonConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.accept()  # Метод для установки соединения.

    async def disconnect(self, code):
        pass

    async def receive_json(self, content, **kwargs):
        await self.send_json(content=content)

    @classmethod
    async def encode_json(cls, content):
        return await super().encode_json(content)

    @classmethod
    async def decode_json(cls, text_data):
        return await super().decode_json(text_data)
