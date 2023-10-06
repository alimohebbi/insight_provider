import json
from collections import Counter

import matplotlib.pyplot as plt
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer
from wordcloud import WordCloud
from gensim import corpora
from gensim.models import LdaModel
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from analyze.preprocessor import pre_process, clean_text_list

nltk.download('vader_lexicon')
nltk.download('stopwords')
nltk.download('punkt')
import pandas as pd


def get_highlights(text):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, sentences_count=5)
    return [str(sentence) for sentence in summary]


def make_word_cloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white', min_word_length=4, max_words=70).generate(
        text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')  # Turn off the axis labels and ticks
    return wordcloud


def sentiment_score(lines):
    scores = []
    for text in lines:
        analyzer = SentimentIntensityAnalyzer()
        sentiment_scores = analyzer.polarity_scores(text)
        scores.append(sentiment_scores['compound'])
    return sum(scores) / len(scores)


def extract_probability_topics(topics):
    cleaned_values = []
    for topic in topics:
        probability = float(topic.split('*')[0])
        name = topic.split('*')[1][1:-1].replace("\"", '')
        cleaned_values.append({'p': probability, 'topic': name})
    return cleaned_values


def get_keywords(topics_prob):
    keyword_prob = []
    for i in topics_prob:
        topics_prob_list = i[1].split('+')

        cleaned_topic_prob = extract_probability_topics(topics_prob_list)
        keyword_prob.extend(cleaned_topic_prob)
    keyword_prob.sort(key=lambda x: x['p'], reverse=True)
    keywords = [item['topic'] for item in keyword_prob]
    return keywords


def get_keywords_domain(documents):
    # Tokenize and preprocess the documents

    stop_words = set(stopwords.words('english'))

    tokenized_documents = [
        [word for word in word_tokenize(doc.lower()) if word.isalnum() and word not in stop_words]
        for doc in documents
    ]

    # Calculate word frequencies
    word_frequencies = Counter(word for doc in tokenized_documents for word in doc)

    # Calculate the number of words to remove (top 1%)
    num_words_to_remove = int(0.001 * len(word_frequencies))

    # Identify the top 0.1% most frequent words to remove
    words_to_remove = [word for word, _ in word_frequencies.most_common(num_words_to_remove)]

    # Filter out high-frequency words from the tokenized documents
    filtered_tokenized_documents = [
        [word for word in doc if word not in words_to_remove]
        for doc in tokenized_documents
    ]

    # Create a dictionary and corpus for LDA
    dictionary = corpora.Dictionary(filtered_tokenized_documents)
    corpus = [dictionary.doc2bow(doc) for doc in filtered_tokenized_documents]

    # Train an LDA model
    lda_model = LdaModel(corpus, num_topics=5, id2word=dictionary, passes=50)

    # Print the top three topics
    topics_prob = lda_model.print_topics(num_topics=5, num_words=20)
    keywords = get_keywords(topics_prob)
    domains = list(set(keywords[:5]))
    keywords = clean_text_list(keywords)
    return domains, keywords
