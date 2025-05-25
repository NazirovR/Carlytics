from django.core.paginator import Paginator
from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect
from .forms import ClientForm, VisitCreateForm, UserRegistrationForm
from .models import Client, Visit
from django.db.models import F, Avg, Count
import json
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .forms import ClientEditForm
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models.functions import ExtractWeekDay, ExtractHour
from collections import defaultdict

@staff_member_required
def dashboard(request):
    # Возраст
    age_groups = {'18-25': 0, '26-35': 0, '36-50': 0, '50+': 0}
    for client in Client.objects.all():
        if 18 <= client.age <= 25:
            age_groups['18-25'] += 1
        elif 26 <= client.age <= 35:
            age_groups['26-35'] += 1
        elif 36 <= client.age <= 50:
            age_groups['36-50'] += 1
        else:
            age_groups['50+'] += 1

    # Пол
    genders = Client.objects.values('gender').annotate(total=Count('gender'))

    # Цели визитов
    purposes = Visit.objects.values('purpose').annotate(total=Count('purpose'))

    # Активность по дням
    visits_by_day = (
        Visit.objects.annotate(date=TruncDate('time_in'))
        .values('date')
        .annotate(total=Count('id'))
        .order_by('date')
    )
    activity_data = {v['date'].strftime('%d.%m'): v['total'] for v in visits_by_day}

    # Повторные визиты
    repeat_visits = (
        Visit.objects.values('client')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
        .count()
    )
    unique_clients = Client.objects.count()
    repeat_data = {
        'Повторные визиты': repeat_visits,
        'Один визит': unique_clients - repeat_visits,
    }

    # Средняя длительность визита по целям
    durations = (
        Visit.objects.annotate(duration=F('time_out') - F('time_in'))
        .values('purpose')
        .annotate(avg_duration=Avg('duration'))
    )
    duration_data = {
        d['purpose']: round(d['avg_duration'].total_seconds() / 3600, 1)
        for d in durations
    }

    # Визиты по дням недели
    weekdays_map = ['ВС', 'ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ']
    weekday_counts = (
        Visit.objects.annotate(weekday=ExtractWeekDay('time_in'))
        .values('weekday')
        .annotate(total=Count('id'))
    )
    weekday_data = {weekdays_map[d['weekday'] - 1]: d['total'] for d in weekday_counts}

    # Визиты по часам
    hour_counts = (
        Visit.objects.annotate(hour=ExtractHour('time_in'))
        .values('hour')
        .annotate(total=Count('id'))
        .order_by('hour')
    )
    hour_data = {f"{d['hour']:02d}:00": d['total'] for d in hour_counts}

    # Пересечение цель + пол + возраст
    cross_data_raw = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for visit in Visit.objects.select_related('client'):
        purpose = visit.purpose or 'Не указано'
        gender = visit.client.gender or 'Не указано'
        age = visit.client.age
        if age is None:
            age_group = 'Не указано'
        elif age <= 25:
            age_group = '18-25'
        elif age <= 35:
            age_group = '26-35'
        elif age <= 50:
            age_group = '36-50'
        else:
            age_group = '50+'
        cross_data_raw[purpose][gender][age_group] += 1

    # Преобразование в сериализуемый формат
    cross_data = {}
    for purpose, gender_dict in cross_data_raw.items():
        for gender, age_dict in gender_dict.items():
            for age_group, count in age_dict.items():
                key = f"{gender} ({age_group})"
                if key not in cross_data:
                    cross_data[key] = {}
                cross_data[key][purpose] = count

    context = {
        'age_data': json.dumps(age_groups),
        'gender_data': json.dumps({g['gender']: g['total'] for g in genders}),
        'purpose_data': json.dumps({p['purpose']: p['total'] for p in purposes}),
        'activity_data': json.dumps(activity_data),
        'repeat_data': json.dumps(repeat_data),
        'duration_data': json.dumps(duration_data),
        'weekday_data': json.dumps(weekday_data),
        'hour_data': json.dumps(hour_data),
        'cross_data': json.dumps(cross_data),
    }
    return render(request, 'analytics/dashboard.html', context)


def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        client_form = ClientForm(request.POST)
        if user_form.is_valid() and client_form.is_valid():
            if Client.objects.filter(phone_number=client_form.cleaned_data['phone_number']).exists():
                messages.error(request, "Пользователь с таким номером уже существует.")
            else:
                user = user_form.save(commit=False)
                user.set_password(user_form.cleaned_data['password'])
                user.save()
                client = client_form.save(commit=False)
                client.user = user
                client.save()
                auth_login(request, user)
                return redirect('visit_create')
    else:
        user_form = UserRegistrationForm()
        client_form = ClientForm()

    return render(request, 'analytics/register.html', {
        'user_form': user_form,
        'client_form': client_form
    })


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            if user.is_staff:
                return redirect('dashboard')
            return redirect('visit_create')
        else:
            messages.error(request, "Неверное имя пользователя или пароль")

    return render(request, 'analytics/login.html')



@login_required
def visit_create(request):
    client = get_object_or_404(Client, user=request.user)

    visit_saved = None

    if request.method == 'POST':
        form = VisitCreateForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.client = client
            duration_hours = form.cleaned_data['duration']
            visit.time_out = visit.time_in + timedelta(hours=duration_hours)
            visit.save()
            form = VisitCreateForm(initial={'time_in': now()})  # очистка формы
            visit_saved = visit
    else:
        form = VisitCreateForm(initial={'time_in': now()})

    # Все визиты клиента, новые вверху
    all_visits = Visit.objects.filter(client=client).order_by('-time_in')

    paginator = Paginator(all_visits, 3)  # по 3 записи на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'analytics/visit_create.html', {
        'form': form,
        'visit_saved': visit_saved,
        'client': client,
        'visits': page_obj,
    })


@login_required
def profile_view(request):
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return redirect('visit_create')

    if request.method == 'POST':
        form = ClientEditForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('visit_create')  # Обновление страницы после сохранения
    else:
        form = ClientEditForm(instance=client)

    return render(request, 'analytics/profile.html', {'form': form, 'client': client})

@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(Visit, pk=pk, client__user=request.user)
    return render(request, 'analytics/visit_detail.html', {'visit': visit})