from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class TaskURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост_Тестовая пост_Тестовая пост',
        )
        cls.template_url_names = {
            reverse('posts:index'): ['posts/index.html', HTTPStatus.OK],
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}):
                ['posts/group_list.html', HTTPStatus.OK],
            reverse('posts:profile', kwargs={'username': cls.user.username}):
                ['posts/profile.html', HTTPStatus.OK],
            reverse('posts:post_detail', kwargs={'post_id': cls.post.pk}):
                ['posts/post_detail.html', HTTPStatus.OK],
            reverse('posts:post_create'):
                ['posts/create_post.html', HTTPStatus.FOUND],
            reverse('posts:post_edit', kwargs={'post_id': cls.post.pk}):
                ['posts/create_post.html', HTTPStatus.FOUND],
        }

    def test_unexisting_page_url_exists_at_desired_location(self):
        """Страница не существует."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_response_urls(self):
        """Проверка доступности на страниц."""
        for address, template in self.template_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, template[1])

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        for address, template in self.template_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template[0])
