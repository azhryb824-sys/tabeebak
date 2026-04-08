from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        label="الاسم الأول",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "اكتب الاسم الأول",
        })
    )
    last_name = forms.CharField(
        max_length=150,
        label="الاسم الأخير",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "اكتب الاسم الأخير",
        })
    )
    username = forms.CharField(
        label="اسم المستخدم",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "اكتب اسم المستخدم",
        })
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "name@example.com",
        })
    )
    phone = forms.CharField(
        label="رقم الجوال",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "05xxxxxxxx",
        })
    )
    user_type = forms.ChoiceField(
        label="نوع الحساب",
        choices=User.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select",
        })
    )
    password1 = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "أدخل كلمة المرور",
        })
    )
    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "أعد إدخال كلمة المرور",
        })
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "phone",
            "user_type",
            "password1",
            "password2",
        )


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="اسم المستخدم",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "أدخل اسم المستخدم",
        })
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "أدخل كلمة المرور",
        })
    )