from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, F
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.management import call_command
from io import StringIO
from .models import Post, Category, Tag, Comment
from .forms import CommentForm, PostForm


class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 9

    def get_queryset(self):
        queryset = Post.objects.filter(
            status='published').select_related('author', 'category')

        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(excerpt__icontains=search_query)
            )

        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Tag filter
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['popular_tags'] = Tag.objects.all()[:15]
        context['recent_posts'] = Post.objects.filter(
            status='published'
        ).order_by('-published_at')[:5]

        # Add stats
        context['posts_count'] = Post.objects.filter(
            status='published').count()
        context['authors_count'] = Post.objects.filter(
            status='published'
        ).values('author').distinct().count()
        context['comments_count'] = Comment.objects.filter(
            is_approved=True).count()

        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        return Post.objects.filter(status='published')

    def get_object(self):
        obj = super().get_object()
        # Increment view count
        Post.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object

        # Get approved comments
        context['comments'] = post.comments.filter(
            is_approved=True, parent=None
        ).select_related('author')

        # Get related posts
        context['related_posts'] = Post.objects.filter(
            status='published',
            category=post.category
        ).exclude(pk=post.pk)[:3]

        # Comment form
        context['comment_form'] = CommentForm()

        return context


class CategoryListView(ListView):
    model = Post
    template_name = 'blog/category_posts.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return Post.objects.filter(
            status='published',
            category=self.category
        ).select_related('author')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = Category.objects.all()
        return context


class TagListView(ListView):
    model = Post
    template_name = 'blog/tag_posts.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return Post.objects.filter(
            status='published',
            tags=self.tag
        ).select_related('author', 'category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        context['popular_tags'] = Tag.objects.all()[:20]
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """View for creating new blog posts"""
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    success_url = reverse_lazy('blog:my_posts')

    def form_valid(self, form):
        form.instance.author = self.request.user

        # Set published_at if status is published
        if form.instance.status == 'published':
            form.instance.published_at = timezone.now()

        messages.success(
            self.request,
            'Your post has been created successfully!' if form.instance.status == 'published'
            else 'Your draft has been saved!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Post'
        context['button_text'] = 'Publish Post'
        return context


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for editing blog posts"""
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    success_url = reverse_lazy('blog:my_posts')

    def test_func(self):
        """Check if user is the author of the post"""
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_staff

    def form_valid(self, form):
        # Update published_at if status changes to published
        if form.instance.status == 'published' and not form.instance.published_at:
            form.instance.published_at = timezone.now()

        messages.success(
            self.request, 'Your post has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Post'
        context['button_text'] = 'Update Post'
        return context


@login_required
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user

            # Handle reply to comment
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)
                comment.parent = parent_comment

            comment.save()
            messages.success(
                request, 'Your comment has been added successfully!')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})

    return redirect(post.get_absolute_url())


class MyPostsView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'blog/my_posts.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # Filter by status if provided in query params
        queryset = Post.objects.filter(
            author=self.request.user).order_by('-created_at')
        status = self.request.GET.get('status')
        if status == 'published':
            queryset = queryset.filter(status='published')
        elif status == 'draft':
            queryset = queryset.filter(status='draft')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['draft_count'] = Post.objects.filter(
            author=self.request.user,
            status='draft'
        ).count()
        context['published_count'] = Post.objects.filter(
            author=self.request.user,
            status='published'
        ).count()
        return context


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View for deleting blog posts"""
    model = Post
    success_url = reverse_lazy('blog:my_posts')

    def test_func(self):
        """Check if user is the author of the post"""
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        """Override delete to add success message"""
        post = self.get_object()
        messages.success(
            request, f'Post "{post.title}" has been deleted successfully!')
        return super().delete(request, *args, **kwargs)


def create_seo_posts(request):
    """
    Admin-only view to create SEO blog posts.
    Access at: /blog/admin/create-seo-posts/
    Can be authenticated via:
    1. Superuser login
    2. Secret key query param matching ADMIN_SECRET_KEY env var
    """
    import os
    secret_key = request.GET.get('key', '')
    admin_secret = os.environ.get('ADMIN_SECRET_KEY', '')

    # Allow access if superuser OR valid secret key
    is_authorized = (
        (request.user.is_authenticated and request.user.is_superuser) or
        (admin_secret and secret_key == admin_secret)
    )

    if not is_authorized:
        return HttpResponse("Unauthorized. Superuser login or valid key required.", status=403)

    # Force publish existing SEO posts that might be in draft
    seo_slugs = [
        'how-long-does-alcohol-withdrawal-last',
        'signs-of-alcoholism-self-assessment',
        'how-to-stop-drinking-alcohol-guide',
        'what-is-sober-curious-guide',
        'high-functioning-alcoholic-signs-help',
        'dopamine-detox-addiction-recovery',
    ]
    updated_count = Post.objects.filter(slug__in=seo_slugs, status='draft').update(status='published')

    # Capture command output
    out = StringIO()
    try:
        call_command('create_seo_blog_posts', stdout=out)
        output = out.getvalue()

        if updated_count > 0:
            output = f"Force-published {updated_count} draft posts.\n\n" + output

        return HttpResponse(
            f"<html><head><title>SEO Posts Created</title></head>"
            f"<body><h1>SEO Blog Posts Creation</h1>"
            f"<pre>{output}</pre>"
            f"<p><a href='/blog/'>View Blog</a></p></body></html>",
            content_type="text/html"
        )
    except Exception as e:
        return HttpResponse(
            f"<html><head><title>Error</title></head>"
            f"<body><h1>Error</h1><pre>{str(e)}</pre></body></html>",
            content_type="text/html",
            status=500
        )
