from django.views.generic import ListView

from .models import Product, Category

# Preferred section order; categories not listed fall back to alphabetical.
CATEGORY_ORDER = ['journals', 'apparel']


class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related('category')
        category_slug = self.request.GET.get('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active = self.request.GET.get('category', '')

        categories = list(
            Category.objects.filter(products__is_active=True).distinct()
        )

        def sort_key(cat):
            try:
                return (0, CATEGORY_ORDER.index(cat.slug))
            except ValueError:
                return (1, cat.name.lower())

        categories.sort(key=sort_key)

        # Group products under their category for a sectioned layout.
        groups = []
        for cat in categories:
            if active and cat.slug != active:
                continue
            products = list(
                cat.products.filter(is_active=True).order_by('-is_featured', '-created_at')
            )
            if products:
                groups.append({'category': cat, 'products': products})

        context['categories'] = categories
        context['category_groups'] = groups
        context['active_category'] = active
        return context
