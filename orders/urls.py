from django.urls import path
from . import views


urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('initiate-payment/', views.initiate_payment, name='initiate_payment'),
    path('payment/ipn/', views.payment_ipn, name='payment_ipn'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/fail/', views.payment_fail, name='payment_fail'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('orders/order_complete/', views.order_complete, name='order_complete'),


    ]
