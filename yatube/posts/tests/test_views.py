from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, Follow

User = get_user_model()


class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='hasnoname')
        cls.new_user = User.objects.create_user(username='idol')
        cls.group = Group.objects.create(
            title='Название группы для теста',
            slug='test-slug',
            description='Тестовое описание группы'
        )
        cls.group_wihtout_posts = Group.objects.create(
            title='Название группы без постов для теста',
            slug='test-withou_posts-slug',
            description='Тестовое описание группы без постов'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст для поста',
            group=cls.group,
            image=cls.uploaded
        )
        cls.comment_form = {
            'text': forms.fields.CharField,
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def common_test(self, post, text, group, author, imag):
        if text:
            self.assertEqual(post.text, self.post.text)
        if group:
            self.assertEqual(post.group.title, self.group.title)
        if author:
            self.assertEqual(post.author, self.post.author)
        if imag:
            self.assertEqual(post.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        cache.clear()
        response = self.guest_client.get(reverse('posts:index'))
        post = response.context['page_obj'][0]
        PostViewsTests.common_test(
            self,
            post,
            text=True,
            group=True,
            author=True,
            imag=True
        )

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        post = response.context['page_obj'][0]
        PostViewsTests.common_test(
            self,
            post,
            text=True,
            group=True,
            author=False,
            imag=True
        )

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': self.user})
        )
        post = response.context['page_obj'][0]
        PostViewsTests.common_test(
            self,
            post,
            text=True,
            group=False,
            author=True,
            imag=True
        )

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(
            response.context['post'].text, 'Тестовый текст для поста'
        )

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_appears_on_pages(self):
        """
        Созданный пост появляется на страницах:
        index, group_list, profile.
        """
        cache.clear()
        urls = (
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.user}),
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                post = response.context['page_obj'][0]
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.group.title, self.post.group.title)

    def test_no_post_in_another_group_page(self):
        """Проверка, что пост не появляется на странице другой группы."""
        response = self.guest_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group_wihtout_posts.slug}))
        posts = response.context['page_obj']
        self.assertEqual(0, len(posts))

    def test_cache_home_page(self):
        """Проверка работы кеша главной страницы."""
        post_del_cache = Post.objects.create(
            text='Текст для проверки',
            author=self.user,
        )

        def response():
            return self.guest_client.get(reverse('posts:index'))

        response_primary = response().content
        post_del_cache.delete()
        response_secondary = response().content
        self.assertEqual(response_primary, response_secondary)
        cache.clear()
        response_cache_clear = response().content
        self.assertNotEqual(response_secondary, response_cache_clear)

    def test_authorized_client_can_follow(self):
        """
        Авторизованный пользователь может подписываться
        на других пользователей.
        """
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.new_user.username}))
        subscribe = Follow.objects.get(user=self.user)
        self.assertEqual(self.new_user, subscribe.author)

    def test_authorized_client_can_unfollow(self):
        """
        Авторизованный пользователь может удалять
        из подписок других пользователей.
        """
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.new_user.username}))
        Follow.objects.get(user=self.user)
        one_follower = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.new_user.username}))
        no_followers = Follow.objects.count()
        self.assertEqual(one_follower - 1, no_followers)

    def test_followers_get_post(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан.
        """
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.new_user.username}))
        idols_post = Post.objects.create(
            text='Тестовый пост кумира',
            group=self.group,
            author=self.new_user,
        )
        user_next = User.objects.create_user(username='dont_like_idol')
        authorized_user_next = Client()
        authorized_user_next.force_login(user_next)
        user_response = self.authorized_client.get(reverse(
            'posts:follow_index'))
        user_next_response = authorized_user_next.get(reverse(
            'posts:follow_index'))
        self.assertEqual(user_response.context['page_obj'][0], idols_post)
        self.assertNotIn(idols_post, user_next_response.context['page_obj'])
