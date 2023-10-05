# Create your views here.
import json
import subprocess
from itertools import chain
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import loader

from utils import normalize_url, url_to_filename
from .forms import WebURLForm
from .models import Company, Documents
from .nlp_tasks import get_highlights, sentiment_score, make_word_cloud, get_topics


def index(request):
    if request.method == 'POST':
        form = WebURLForm(request.POST)
        if form.is_valid():
            target_url = normalize_url(form.cleaned_data['target_url'])
            request.session['target_url'] = target_url
            return HttpResponseRedirect(f'/analyze/progress/')

        else:
            return render(request, 'analyze/index.html', {'form': form})

    form = WebURLForm()
    return render(request, 'analyze/index.html', {'form': form})


def results(request, company_id):
    company = Company.objects.get(id=company_id)
    top_companies = Company.objects.order_by('-sentiment_score')[:3]
    top_companies_names = [(company.website_url, round(company.sentiment_score, 3), company.id) for company in
                           top_companies]
    company_sentiment_rank = Company.objects.filter(sentiment_score__gt=company.sentiment_score).count() + 1
    template = loader.get_template("analyze/results.html")
    number_of_companies = Company.objects.count()

    context = {
        "company": company,
        "top_companies": top_companies_names,
        'sentiment_rank': company_sentiment_rank,
        'total_companies': number_of_companies
    }

    return HttpResponse(template.render(context, request))


def progress(request):
    target_url = request.session.get('target_url')
    return render(request, 'analyze/progress.html', {'target_url': target_url})


def get_insight(request):
    if request.method == 'POST':
        # Get the JSON data from the request body
        try:
            data = json.loads(request.body)
            target_url = data.get('target_url')
            insight_id = get_or_create_insight(target_url)
            response_data = {'message': 'ok', 'insight_id': insight_id}
            return JsonResponse(response_data)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)

    return JsonResponse({'message': 'Invalid request method'}, status=400)


def get_or_create_insight(target_url):
    try:
        company = Company.objects.get(website_url=target_url)
    except Company.DoesNotExist:
        # scrap_website(target_url)
        insight = analyze_info(target_url)

        company = Company(website_url=target_url, sentiment_score=insight['score'],
                          highlights=insight['highlights'], topics=insight['topics'])
        with Path(insight['image_address']).open(mode="rb") as f:
            company.word_cloud = File(f, name=Path(insight['image_address']).name)
            company.save()
        documents = Documents(scrapped_documents=insight['documents'], company = company)
        documents.save()
    return company.id


def scrap_website(target_url) -> None:
    result = subprocess.run(
        ["/Users/usiusi/Documents/Repositories/web_insight/venv/bin/python", "analyze/scraper.py", target_url],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def analyze_info(target_url) -> dict:
    delimiter = '.\r'
    with open('scrapy_dump.json', 'r') as json_file:
        documents = json.load(json_file)
    lines = list(chain(*documents))

    full_text = delimiter.join(lines)

    word_cloud = make_word_cloud(full_text)
    image_address = 'word_cloud.png'
    word_cloud.to_file(image_address)
    highlights = get_highlights(text=full_text)
    score = sentiment_score(lines)
    document_for_topics = [" ".join(sentences) for sentences in documents]
    topics = get_topics(document_for_topics)

    return {'score': score, 'highlights': highlights, 'image_address': image_address, 'topics': topics,
            'documents': documents}
