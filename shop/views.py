from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistrasiForm, ProdukForm
from .models import Produk, Pesanan, DetailPesanan, AktivitasPengguna
from django.contrib.auth import get_user_model
from .models import Produk, Pesanan, DetailPesanan, Pengguna, AktivitasPengguna
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.db.models import Sum

User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = RegistrasiForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistrasiForm()
    return render(request, 'shop/auth.html', {'form': form, 'aksi': 'Registrasi'})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'shop/auth.html', {'form': form, 'aksi': 'Login'})

def logout_view(request):
    logout(request)
    return redirect('login')

def admin_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'admin':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Anda tidak memiliki hak akses ke halaman ini.")
    return _wrapped_view_func

@login_required
def home_view(request):
    if request.user.role == 'admin':
        return redirect('admin_dashboard')
    return redirect('user_dashboard')
@admin_required
def admin_dashboard(request):
    # PERBAIKAN UTAMA: Menyuntikkan filter status='selesai' sebelum menghitung total harga
    # Perintah 'or 0' di ujung berfungsi sebagai tameng agar halaman tidak eror jika belum ada transaksi yang selesai
    total_pendapatan = Pesanan.objects.filter(status='selesai').aggregate(Sum('total_harga'))['total_harga__sum'] or 0
    
    # Jika Anda ingin volume transaksi juga hanya menghitung pesanan yang sukses, gunakan baris ini:
    total_produk_terjual = Pesanan.objects.filter(status='selesai').count()
    
    # Menghitung sisa data analitik pelengkap dasbor admin
    total_pengguna = Pengguna.objects.filter(role='user').count()
    stok_kritis = Produk.objects.filter(stok__lte=3)
    daftar_produk = Produk.objects.all()
    
    context = {
        'total_pendapatan': total_pendapatan,
        'total_produk_terjual': total_produk_terjual,
        'total_pengguna': total_pengguna,
        'stok_kritis': stok_kritis,
        'daftar_produk': daftar_produk,
    }
    return render(request, 'shop/admin_dashboard.html', context)

@login_required
@never_cache
def user_dashboard(request):
    daftar_produk = Produk.objects.all()
    produk_rekomendasi = []
    
    # LANGKAH UTAMA: Tarik memori kata kunci pencarian terakhir dari session
    query_terakhir = request.session.get('terakhir_dicari', '')
    
    produk_acuan_kategori = None
    kata_kunci_acuan = []
    id_produk_dikecualikan = None
    
    # KONDISI A: Jika pengguna memiliki riwayat pencarian terbaru, jadikan ini prioritas utama
    if query_terakhir:
        kata_kunci_acuan = query_terakhir.split()
        semua_kategori = Produk.objects.values_list('kategori', flat=True).distinct()
        max_skor = 0
        
        # Menerapkan scoring pencarian untuk menebak kategori apa yang diinginkan user
        for kat in semua_kategori:
            kat_lower = kat.lower()
            kat_words = kat_lower.split()
            skor = 0
            for word_kat in kat_words:
                if word_kat in kata_kunci_acuan:
                    skor += 5
            if skor > max_skor:
                max_skor = skor
                produk_acuan_kategori = kat
                
        if max_skor < 3:
            produk_acuan_kategori = None

    # KONDISI B: Jika belum pernah mencari, gunakan riwayat transaksi terakhir sebagai cadangan
    if not produk_acuan_kategori and not kata_kunci_acuan:
        item_terakhir = DetailPesanan.objects.filter(
            pesanan__pembeli=request.user
        ).select_related('produk').last()
        
        if item_terakhir and item_terakhir.produk:
            produk_acuan_kategori = item_terakhir.produk.kategori
            kata_kunci_acuan = item_terakhir.produk.nama.split()
            id_produk_dikecualikan = item_terakhir.produk.pk

    # EKSEKUSI PRODUK REKOMENDASI: Jika salah satu dari dua kondisi di atas terpenuhi
    if produk_acuan_kategori or kata_kunci_acuan:
        query_nama = Q()
        for kata in kata_kunci_acuan:
            if len(kata) > 2:
                query_nama |= Q(nama__icontains=kata)
        
        # Filter akurat: Wajib satu kategori dan judul namanya mirip
        rekomendasi_akurat = Produk.objects.all()
        if produk_acuan_kategori:
            rekomendasi_akurat = rekomendasi_akurat.filter(kategori=produk_acuan_kategori)
        if query_nama:
            rekomendasi_akurat = rekomendasi_akurat.filter(query_nama)
        if id_produk_dikecualikan:
            rekomendasi_akurat = rekomendasi_akurat.exclude(pk=id_produk_dikecualikan)
            
        rekomendasi_akurat = rekomendasi_akurat.distinct()
        
        # Filter cadangan: Produk lain yang berada di dalam kategori yang sama
        cadangan_kategori = Produk.objects.all()
        if produk_acuan_kategori:
            cadangan_kategori = cadangan_kategori.filter(kategori=produk_acuan_kategori)
        if id_produk_dikecualikan:
            cadangan_kategori = cadangan_kategori.exclude(pk=id_produk_dikecualikan)
            
        cadangan_kategori = cadangan_kategori.distinct()
        
        # Menggabungkan hasil akurat dan cadangan ke dalam satu list
        daftar_gabungan = list(rekomendasi_akurat)
        for prod in cadangan_kategori:
            if prod not in daftar_gabungan:
                daftar_gabungan.append(prod)
                
        # Mengunci tampilan dasbor tepat 5 produk relevan teratas
        produk_rekomendasi = daftar_gabungan[:5]
        
    context = {
        'daftar_produk': daftar_produk,
        'produk_rekomendasi': produk_rekomendasi,
    }
    return render(request, 'shop/user_dashboard.html', context)
@admin_required
def produk_tambah(request):
    if request.method == 'POST':
        form = ProdukForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = ProdukForm()
    return render(request, 'shop/produk_form.html', {'form': form, 'aksi': 'Tambah'})

@admin_required
def produk_ubah(request, pk):
    produk = get_object_or_404(Produk, pk=pk)
    if request.method == 'POST':
        form = ProdukForm(request.POST, request.FILES, instance=produk)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = ProdukForm(instance=produk)
    return render(request, 'shop/produk_form.html', {'form': form, 'aksi': 'Ubah'})

@admin_required
def produk_hapus(request, pk):
    produk = get_object_or_404(Produk, pk=pk)
    if request.method == 'POST':
        produk.delete()
        return redirect('admin_dashboard')
    return render(request, 'shop/produk_konfirmasi_hapus.html', {'produk': produk})
@login_required
def beli_produk(request, pk):
    if request.method == 'POST':
        produk = get_object_or_404(Produk, pk=pk)
        if produk.stok > 0:
        
            produk.stok -= 1
            produk.save()
            
        
            pesanan = Pesanan.objects.create(pembeli=request.user, total_harga=produk.harga, status='proses')
            DetailPesanan.objects.create(pesanan=pesanan, produk=produk, jumlah=1, harga_satuan=produk.harga)
            
            
            AktivitasPengguna.objects.create(pengguna=request.user, produk=produk, jenis_aktivitas='beli')
            
    
    return redirect('user_dashboard')
def hitung_skor_kemiripan(deskripsi_produk, kata_kunci_kesukaan):
    
    skor = 0
    deskripsi_lower = deskripsi_produk.lower()
    for kata in kata_kunci_kesukaan:
        if kata in deskripsi_lower:
            skor += 1
    return skor
def daftar_pengguna_view(request):
    daftar_pengguna = User.objects.all()
    
    context = {
        'daftar_pengguna': daftar_pengguna,
    }
    return render(request, 'shop/daftar_pengguna.html', context)
def detail_produk_view(request, pk):
    produk = get_object_or_404(Produk, pk=pk)
    produk_mirip = []
    if produk.kategori:
        produk_mirip = Produk.objects.filter(kategori=produk.kategori).exclude(pk=pk)[:4]
    context = {
        'produk': produk,
        'produk_mirip': produk_mirip,
    }
    return render(request, 'shop/detail_produk.html', context)
def checkout_view(request, pk):
    produk = get_object_or_404(Produk, pk=pk)
    context = {
        'produk': produk,
        'pembeli': request.user,
    }
    return render(request, 'shop/checkout.html', context)
def hitung_jarak(s1, s2):
    # Fungsi manual menghitung kedekatan karakter untuk toleransi typo (Levenshtein Distance)
    if len(s1) < len(s2):
        return hitung_jarak(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    s1 = s1.lower()
    s2 = s2.lower()
    
    baris_sebelumnya = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        baris_sekarang = [i + 1]
        for j, c2 in enumerate(s2):
            sisip = baris_sebelumnya[j + 1] + 1
            hapus = baris_sekarang[j] + 1
            ganti = baris_sebelumnya[j] + (c1 != c2)
            baris_sekarang.append(min(sisip, hapus, ganti))
        baris_sebelumnya = baris_sekarang
    return baris_sebelumnya[-1]

def search_view(request):
    query = request.GET.get('q', '').strip().lower()
    hasil_produk = []
    
    if query:
        # Menyimpan kata kunci pencarian terakhir ke dalam memori session untuk data rekomendasi dasbor
        request.session['terakhir_dicari'] = query
        
        # Kamus perluasan kata manual termasuk Jenis Barang dan Sinonim Gender
        kamus_sinonim = {
            'pakai': ['baju', 'pakaian', 'kaos', 'kemeja', 'busana'],
            'baju': ['pakaian', 'kaos', 'kemeja', 'pakai', 'busana'],
            'pakaian': ['baju', 'kaos', 'kemeja', 'pakai', 'busana'],
            'celana': ['jeans', 'bawahan', 'kulot', 'lewis'],
            'sepatu': ['sneakers', 'alas kaki', 'sandal', 'selop'],
            'pria': ['laki', 'cowok', 'lelaki', 'boys', 'men'],
            'laki': ['pria', 'cowok', 'lelaki', 'boy', 'man'],
            'wanita': ['perempuan', 'cewek', 'gadis', 'girls', 'women'],
            'perempuan': ['wanita', 'cewek', 'gadis', 'girl', 'woman']
        }
        
        kata_kunci = query.split()
        kumpulan_kata_pencarian = set(kata_kunci)
        
        for kata in kata_kunci:
            if kata in kamus_sinonim:
                kumpulan_kata_pencarian.update(kamus_sinonim[kata])
        
        semua_kategori = Produk.objects.values_list('kategori', flat=True).distinct()
        kategori_terdeteksi_list = []
        max_skor = 0
        
        for kat in semua_kategori:
            kat_lower = kat.lower()
            kat_words = kat_lower.split()
            skor = 0
            
            for word_kat in kat_words:
                if word_kat in kata_kunci:
                    skor += 5
                elif word_kat in kumpulan_kata_pencarian:
                    skor += 3
                else:
                    for kata_user in kata_kunci:
                        if len(kata_user) > 3 and hitung_jarak(kata_user, word_kat) <= 1:
                            skor += 2
                            break
            
            if skor > max_skor:
                max_skor = skor
                kategori_terdeteksi_list = [kat]
            elif skor == max_skor and skor > 0:
                kategori_terdeteksi_list.append(kat)
        
        if max_skor < 3:
            kategori_terdeteksi_list = []
            
        produk_basis = Produk.objects.all()
        
        if kategori_terdeteksi_list:
            produk_basis = produk_basis.filter(kategori__in=kategori_terdeteksi_list)
            
        for prod in produk_basis:
            nama_lower = prod.nama.lower()
            kategori_prod_lower = prod.kategori.lower()
            memenuhi_syarat = False
            
            # PERBAIKAN UTAMA: Pecah kalimat secara bersih menjadi kata utuh untuk mencegah "tas" masuk ke "atasan"
            nama_bersih = nama_lower.replace("-", " ").replace("/", " ")
            nama_words = [w.strip(".,-_()") for w in nama_bersih.split()]
            
            kategori_bersih = kategori_prod_lower.replace("-", " ").replace("/", " ")
            kategori_words = [w.strip(".,-_()") for w in kategori_bersih.split()]
            
            for kata in kumpulan_kata_pencarian:
                # Sekarang sistem mencocokkan kesamaan kata secara utuh, bukan potongan huruf lagi
                if kata in nama_words or kata in kategori_words:
                    memenuhi_syarat = True
                    break
                
                # Toleransi salah ketik tetap berjalan aman khusus untuk kata yang panjang (di atas 3 huruf)
                for bagian_nama in nama_words:
                    if len(kata) > 3 and hitung_jarak(kata, bagian_nama) <= 1:
                        memenuhi_syarat = True
                        break
            
            if memenuhi_syarat:
                hasil_produk.append(prod)
                
    context = {
        'query': query,
        'hasil_produk': hasil_produk,
    }
    return render(request, 'shop/search.html', context)

def search_suggestions(request):
    # Fungsi khusus melayani dropdown rekomendasi saat user mengetik (AJAX Endpoint)
    query = request.GET.get('q', '').strip().lower()
    daftar_rekomendasi = []
    
    if len(query) >= 1:
        # Mencari nama produk dan nama kategori yang mengandung teks ketikan pengguna
        produk_cocok = Produk.objects.filter(nama__icontains=query).values_list('nama', flat=True)[:5]
        kategori_cocok = Produk.objects.filter(kategori__icontains=query).values_list('kategori', flat=True).distinct()[:3]
        
        daftar_rekomendasi.extend(list(kategori_cocok))
        daftar_rekomendasi.extend(list(produk_cocok))
        
        # Membersihkan duplikasi kata dan mengambil 6 saran teratas
        daftar_rekomendasi = list(dict.fromkeys(daftar_rekomendasi))[:6]
        
    return JsonResponse({'suggestions': daftar_rekomendasi})
def admin_pesanan_view(request):
    # Mengambil semua pesanan dari transaksi terbaru ke transaksi terlama
    # select_related dan prefetch_related digunakan untuk menarik data pembeli dan item produk secara borongan
    daftar_pesanan = Pesanan.objects.select_related('pembeli').prefetch_related('item_pesanan__produk').order_by('-tanggal_transaksi')
    
    context = {
        'daftar_pesanan': daftar_pesanan,
    }
    return render(request, 'shop/admin_pesanan.html', context)

def update_status_pesanan(request, pk, opsi):
    pesanan = get_object_or_404(Pesanan, pk=pk)
    
    # Memproses perubahan status berdasarkan opsi tombol yang ditekan admin
    if opsi == 'selesai':
        pesanan.status = 'selesai'
    elif opsi == 'batal':
        pesanan.status = 'batal'
        
    pesanan.save()
    
    # Kembalikan respon berbasis JSON agar halaman tidak perlu melakukan reload/refresh
    return JsonResponse({
        'status': 'success',
        'new_status': pesanan.status,
        'status_display': pesanan.get_status_display()
    })