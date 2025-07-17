from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)  # Correct model name (Product)
    product_variation = []
    if request.method == 'POST':
        for item in request.POST:
            key = item
            value = request.POST[key]


            try:
                Variation = Variation.objects.get(product=product, variation_category_iexact=key, variation_value_iexact=value)
                product_variation.append(Variation)
            except:
                pass



    try:
        cart = Cart.objects.get(card_id=_cart_id(request))  # Use 'card_id' instead of 'cart_id'
    except Cart.DoesNotExist:
        cart = Cart.objects.create(
            card_id=_cart_id(request)  # Use 'card_id' here too
        )
    cart.save()
    is_cart_item_exits = CartItem.objects.filter(product=product, Cart=cart).exists()
    if is_cart_item_exits:
        cart_item = CartItem.objects.filter(product=product, Cart=cart)  # Use 'Cart' instead of 'cart'
        # existing_variations --> databae
        #current variations -> product_variation
        #item_id -> database
        ex_var_list =[]
        id = []
        for item in cart_item:
            existing_variation = item.Variation.all()
            ex_var_list.append(list(existing_variation))
            id.append(item.id)

            print(ex_var_list)

            if product_variation in ex_var_list:
                # increse the cart item quantity
                index = ex_var_list.index(product_variation)
                item_id = id[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()

            else:
                item = CartItem.objects.create(product=product, quantity=1, Cart=cart)
                if len(product_variation) > 0:
                    item.Variation.clear()
                    item.Variation.add(*product_variation)
                item.save()
    else:
        cart_item = CartItem.objects.create(
            product=product,
            quantity=1,
            Cart=cart,  # Use 'Cart' instead of 'cart'
        )
        if len(product_variation) > 0:
            cart_item.Variation.clear()
            cart_item.Variation.add(* product_variation)
        cart_item.save()
    return redirect('cart')

def remove_cart(request, product_id):
    cart = Cart.objects.get(card_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    try:
        cart_item = CartItem.objects.get(Cart_id=cart.id, product=product)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')

def remove_cart_item(request, product_id):
    cart = Cart.objects.get(card_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.get(Cart_id=cart.id, product=product)
    cart_item.delete()
    return redirect('cart')

def cart(request, total=0, quantity=0, cart_items=None):
    try:
        cart = Cart.objects.get(card_id=_cart_id(request))
        cart_items = CartItem.objects.filter(Cart=cart, is_active=True)  # Change cart to Cart
        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity  # Corrected calculation
            quantity += cart_item.quantity  # Fixed typo 'c cart_item.quantity'
        tax = (15 * total)/100
        grand_total = total + tax

    except Cart.DoesNotExist:
        cart_items = []
        tax = 0
        grand_total = 0

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/cart.html', context)


from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem

@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
    try:
        cart = Cart.objects.get(card_id=_cart_id(request))
        cart_items = CartItem.objects.filter(Cart=cart, is_active=True)

        # ✅ Assign user to each CartItem if not already assigned
        for item in cart_items:
            if item.user is None:
                item.user = request.user
                item.save()

        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity
        tax = (15 * total) / 100
        grand_total = total + tax

    except Cart.DoesNotExist:
        cart_items = []
        tax = 0
        grand_total = 0

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/checkout.html', context)
