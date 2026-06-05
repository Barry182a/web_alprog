from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Pengguna
from .models import Produk

class RegistrasiForm(UserCreationForm):
    role = forms.ChoiceField(choices=Pengguna.ROLE_CHOICES, required=True, label="Daftar Sebagai")

    class Meta(UserCreationForm.Meta):
        model = Pengguna
        fields = UserCreationForm.Meta.fields + ('email', 'role')
class ProdukForm(forms.ModelForm):
    class Meta:
        model = Produk
        fields = ['nama', 'kategori', 'harga', 'stok', 'deskripsi', 'gambar']
        
    