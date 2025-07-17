import json
import datetime
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.core.mail import EmailMessage
from .models import Order, OrderProduct, Payment
from carts.models import CartItem
from store.models import Product
from .forms import OrderForm
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

def place_order(request, total=0, quantity=0):
    current_user = request.user

    #if the cart is less than or equal to 0, then redirect back to shop

    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (15 * total)/100
    grand_total = total + tax


    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing info inside order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total  # Make sure this is defined earlier
            data.tax = tax  # Make sure this is defined earlier
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            #Generate order number

            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20250305
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total
            }
            return render(request, 'orders/payments.html', context)


    else:
        return redirect('checkout')

def initiate_payment(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        try:
            order = Order.objects.get(id=order_id, is_ordered=False)
        except Order.DoesNotExist:
            messages.error(request, "Invalid Order ID.")
            return redirect('store')

        sslcommerz_url = (
            'https://sandbox.sslcommerz.com/gwprocess/v4/api.php'
            if settings.SSLCOMMERZ_SANDBOX else
            'https://securepay.sslcommerz.com/gwprocess/v4/api.php'
        )

        payload = {
            "store_id": settings.SSLCOMMERZ_STORE_ID,
            "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
            "total_amount": str(order.order_total),
            "currency": "BDT",
            "tran_id": order.order_number,
            "success_url": request.build_absolute_uri(reverse('payment_success')),
            "fail_url": request.build_absolute_uri(reverse('payment_fail')),
            "cancel_url": request.build_absolute_uri(reverse('payment_cancel')),
            "ipn_url": request.build_absolute_uri(reverse('payment_ipn')),
            "cus_name": f"{order.first_name} {order.last_name}",
            "cus_email": order.email,
            "cus_add1": order.address_line_1,
            "cus_city": order.city,
            "cus_state": order.state,
            "cus_country": order.country,
            "cus_phone": order.phone,
            "shipping_method": "NO",
            "product_name": "Order Payment",
            "product_category": "General",
            "product_profile": "general",
        }

        try:
            response = requests.post(sslcommerz_url, data=payload)
            response_data = response.json()

            if response_data.get("status") == "SUCCESS":
                return redirect(response_data.get("GatewayPageURL"))
            else:
                messages.error(request, "Failed to initiate payment.")
        except Exception as e:
            messages.error(request, f"Payment initiation error: {e}")
    return redirect('place_order')


@csrf_exempt
def payment_ipn(request):
    if request.method == 'POST':
        data = request.POST
        tran_id = data.get('tran_id')
        val_id = data.get('val_id')
        status = data.get('status')

        try:
            order = Order.objects.get(order_number=tran_id, is_ordered=False)
        except Order.DoesNotExist:
            return HttpResponse('Order not found', status=404)

        validation_url = (
            f"https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php?val_id={val_id}"
            f"&store_id={settings.SSLCOMMERZ_STORE_ID}&store_passwd={settings.SSLCOMMERZ_STORE_PASSWORD}"
            "&v=1&format=json"
        )

        try:
            response = requests.get(validation_url)
            validation = response.json()

            if validation['status'] in ['VALID', 'VALIDATED']:
                payment = Payment.objects.create(
                    user=order.user,
                    payment_id=val_id,
                    payment_method=data.get('card_type', 'SSLCOMMERZ'),
                    amount_paid=order.order_total,
                    status=status
                )
                order.payment = payment
                order.is_ordered = True
                order.save()

                cart_items = CartItem.objects.filter(user=order.user)
                for item in cart_items:
                    OrderProduct.objects.create(
                        order=order,
                        payment=payment,
                        user=order.user,
                        product=item.product,
                        quantity=item.quantity,
                        product_price=item.product.price,
                        ordered=True
                    )
                    item.product.stock -= item.quantity
                    item.product.save()

                cart_items.delete()
                return HttpResponse('Payment recorded', status=200)
            else:
                return HttpResponse('Invalid payment', status=400)
        except Exception as e:
            return HttpResponse(f"Validation error: {e}", status=400)
    return HttpResponse('Invalid request', status=400)

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from .models import Order, Payment, OrderProduct
from carts.models import CartItem
from django.contrib import messages

@csrf_exempt
def payment_success(request):
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    payment_method = request.POST.get('card_issuer') or 'SSLCOMMERZ'
    status = request.POST.get('status') or 'VALID'

    if not tran_id:
        messages.error(request, "Transaction ID is missing.")
        return redirect('store')

    try:
        order = Order.objects.get(order_number=tran_id, is_ordered=False)
        user = order.user  # ✅ Get user from the order

        # Save payment
        payment = Payment.objects.create(
            user=user,
            payment_id=tran_id,
            payment_method=payment_method,
            amount_paid=order.order_total,
            status=status,
        )

        # Update order
        order.payment = payment
        order.is_ordered = True
        order.save()

        # Move cart items to OrderProduct
        cart_items = CartItem.objects.filter(user=user)
        for item in cart_items:
            OrderProduct.objects.create(
                order=order,
                payment=payment,
                user=user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True,
            )
        cart_items.delete()

        # Render order complete page
        ordered_products = OrderProduct.objects.filter(order=order)
        subtotal = sum(item.product_price * item.quantity for item in ordered_products)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)

        # send emaill to user
        mail_subject = 'Thank You For Your Order!'
        message = render_to_string('orders/order_recived_email.html',{

            'user' : request.user,
            'order' : order,
            'ordered_products': ordered_products,
            'payment': payment,
            'subtotal': subtotal,
        })
        to_email = request.user.email
        send_email = EmailMessage(mail_subject, message, to=[to_email])
        send_email.send()

    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('store')

def payment_fail(request):
    messages.error(request, "Payment failed.")
    return redirect('store')


def payment_cancel(request):
    messages.warning(request, "Payment was cancelled.")
    return redirect('store')


def order_complete(request):
    order_number = request.GET.get('order_number')
    payment_id = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)
        payment = Payment.objects.get(payment_id=payment_id)
        subtotal = sum(item.product_price * item.quantity for item in ordered_products)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'payment': payment,
            'order_number': order.order_number,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Order.DoesNotExist, Payment.DoesNotExist):
        return redirect('home')
