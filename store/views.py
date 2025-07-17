from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating, ProductGallery
from .models import category
from category.models import category
from carts.models import Cart
from carts.models import CartItem

from carts.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from .forms import ReviewForm
from django.contrib import messages
from orders.models import OrderProduct


def store(request, category_slug=None):
        Categories = None
        products = None

        if category_slug != None:
            Categories = get_object_or_404(category, slug=category_slug)
            products = Product.objects.filter(category=Categories, is_available=True)
            paginator = Paginator(products, 1)
            page = request.GET.get('page')
            paged_products = paginator.get_page(page)
            product_count = products.count()
        else:
            products = Product.objects.all().filter(is_available=True).order_by('id')
            paginator = Paginator(products, 3)
            page = request.GET.get('page')
            paged_products = paginator.get_page(page)
            product_count = products.count()

        context ={
             'products': paged_products,
             'product_count': product_count,
        }
        return render(request, 'store/store.html', context)



def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(Cart__card_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e

    if request.user.is_authenticated:
        try:
            orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
        except OrderProduct.DoesNotExist:
            orderproduct = None
    else:
        orderproduct = None

        # Get the Reviews
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)

    # Get the product Gallary
    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)

    context = {
        'single_product': single_product,
        'in_cart'       : in_cart,
        'orderproduct' : orderproduct,
        'reviews' : reviews,
        'product_gallery': product_gallery,
    }
    return render(request, 'store/product_detail.html', context)



def search(request):
    keyword = request.GET.get('keyword')
    products = []
    product_count = 0

    if keyword:
        products = Product.objects.filter(product_name__icontains=keyword, is_available=True)
        product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)


from django.contrib import messages
from django.shortcuts import redirect
from .models import ReviewRating
from .forms import ReviewForm
def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    product = Product.objects.get(id=product_id)

    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            if form.is_valid():
                form.save()
                messages.success(request, 'Thank you! Your review has been updated.')
                return redirect(url)
            else:
                messages.error(request, 'Error updating review. Please correct the form.')
                print("Update errors:", form.errors)

        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = float(form.cleaned_data['rating'])  # Important
                data.review = form.cleaned_data['review']
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
                return redirect(url)
            else:
                messages.error(request, 'Error submitting review. Please correct the form.')
                print("New review errors:", form.errors)

        # if form fails
        return render(request, 'your_template.html', {
            'form': form,
            'single_product': product,
        })

    return redirect(url)
