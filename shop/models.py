from django.db import models
from django.contrib.auth.models import AbstractUser

class Pengguna(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'Pengguna/User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

class Produk(models.Model):
    nama = models.CharField(max_length=255)
    kategori = models.CharField(max_length=100, default='Umum')
    gambar = models.ImageField(upload_to='produk_images/', blank=True, null=True)
    deskripsi = models.TextField()
    harga = models.DecimalField(max_digits=12, decimal_places=2)
    stok = models.IntegerField(default=0)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama

class Pesanan(models.Model):
    STATUS_CHOICES = (
        ('proses', 'Diproses'),
        ('kirim', 'Dikirim'),
        ('selesai', 'Selesai'),
    )
    pembeli = models.ForeignKey(Pengguna, on_delete=models.CASCADE, related_name='daftar_pesanan')
    total_harga = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='proses')
    tanggal_transaksi = models.DateTimeField(auto_now_add=True)

class DetailPesanan(models.Model):
    pesanan = models.ForeignKey(Pesanan, on_delete=models.CASCADE, related_name='item_pesanan')
    produk = models.ForeignKey(Produk, on_delete=models.SET_NULL, null=True)
    jumlah = models.IntegerField(default=1)
    harga_satuan = models.DecimalField(max_digits=12, decimal_places=2)

class AktivitasPengguna(models.Model):
    pengguna = models.ForeignKey(Pengguna, on_delete=models.CASCADE)
    produk = models.ForeignKey(Produk, on_delete=models.CASCADE)
    jenis_aktivitas = models.CharField(max_length=20, default='lihat')
    waktu = models.DateTimeField(auto_now_add=True)