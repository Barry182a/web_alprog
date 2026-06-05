from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('admin-dashboard/produk/tambah/', views.produk_tambah, name='produk_tambah'),
    path('admin-dashboard/produk/ubah/<int:pk>/', views.produk_ubah, name='produk_ubah'),
    path('admin-dashboard/produk/hapus/<int:pk>/', views.produk_hapus, name='produk_hapus'),
    path('user-dashboard/beli/<int:pk>/', views.beli_produk, name='beli_produk'),
    path('admin-dashboard/pengguna/', views.daftar_pengguna_view, name='daftar_pengguna'),
    path('produk/<int:pk>/', views.detail_produk_view, name='detail_produk'),
    path('checkout/<int:pk>/', views.checkout_view, name='checkout'),
    path('pencarian/', views.search_view, name='pencarian_produk'),
    path('pencarian/rekomendasi-kata/', views.search_suggestions, name='rekomendasi_kata'),
    path('admin-dashboard/pesanan/', views.admin_pesanan_view, name='admin_pesanan'),
    path('admin-dashboard/pesanan/<int:pk>/status/<str:opsi>/', views.update_status_pesanan, name='update_status_pesanan'),
]