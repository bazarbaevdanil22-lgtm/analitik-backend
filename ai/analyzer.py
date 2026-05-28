import logging
import re
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from transformers import pipeline
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        top_k=None
    )
    AI_AVAILABLE = True
    logger.info("AI models loaded successfully")
except Exception as e:
    logger.warning(f"AI models not available: {e}. Using rule-based fallback.")
    AI_AVAILABLE = False

STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
    'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'just', 'because', 'but', 'and', 'or', 'if', 'while', 'although',
    'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we',
    'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself',
    'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself',
    'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
    'what', 'which', 'who', 'whom', 'about', 'up', 'down', 'just',
    'also', 'very', 'really', 'please', 'thank', 'would', 'could',
}

CATEGORY_KEYWORDS = {
    'complaint': [
        'complaint', 'complain', 'unhappy', 'dissatisfied', 'unsatisfied',
        'bad', 'terrible', 'awful', 'horrible', 'worst', 'poor',
        'broken', 'damage', 'damaged', 'defective', 'faulty', 'useless',
        'waste', 'not working', 'doesn\'t work', 'failed', 'issue',
        'problem', 'mistake', 'error', 'bug', 'wrong', 'incorrect',
        'missing', 'late', 'delay', 'refund', 'money back',
    ],
    'suggestion': [
        'suggest', 'suggestion', 'recommend', 'recommendation', 'propose',
        'proposal', 'idea', 'improve', 'improvement', 'better', 'upgrade',
        'enhance', 'feature', 'would be nice', 'could add', 'should add',
        'why not', 'how about', 'consider', 'option', 'would like to see',
    ],
    'question': [
        'question', 'how', 'what', 'when', 'where', 'which', 'who',
        'why', 'can you', 'could you', 'would you', 'do you',
        'is there', 'are there', 'tell me', 'help me understand',
        'i want to know', 'i wonder', 'not sure', 'clarify',
        'explain', 'meaning', 'what is', 'how to', 'how do',
    ],
    'praise': [
        'great', 'amazing', 'excellent', 'wonderful', 'fantastic',
        'love', 'best', 'perfect', 'happy', 'pleased', 'satisfied',
        'grateful', 'thankful', 'thanks', 'appreciate', 'awesome',
        'brilliant', 'outstanding', 'superb', 'incredible',
        'good job', 'well done', 'impressed', 'exceptional',
    ],
    'bugreport': [
        'bug', 'crash', 'freeze', 'glitch', 'error', 'not working',
        'doesn\'t work', 'failed', 'failure', 'unexpected',
        'exception', 'break', 'broken', 'malfunction', 'defect',
        'misbehave', 'misbehavior', 'hang', 'stuck', 'won\'t load',
        'blank screen', 'not responding', 'error message',
    ],
}

PRIORITY_KEYWORDS = {
    'critical': [
        'urgent', 'critical', 'emergency', 'immediately', 'asap',
        'blocked', 'cannot work', 'down', 'outage', 'security',
        'data loss', 'crash', 'urgently', 'deadline', 'passed',
    ],
    'high': [
        'important', 'high priority', 'significant', 'major',
        'serious', 'severe', 'frustrated', 'angry', 'furious',
        'terrible', 'horrible', 'very bad', 'extremely',
    ],
    'medium': [
        'medium', 'moderate', 'somewhat', 'annoying', 'inconvenient',
        'frustrating', 'minor', 'slightly', 'would like',
    ],
}

def analyze_emotion(text):
    if AI_AVAILABLE:
        try:
            results = sentiment_pipeline(text[:512])
            if results and len(results) > 0:
                scores = {item['label'].lower(): item['score'] for item in results[0]}
                if 'positive' in scores and 'negative' in scores:
                    pos, neg = scores['positive'], scores['negative']
                    if pos > 0.6:
                        return 'positive', round(pos, 4)
                    elif neg > 0.6:
                        return 'negative', round(neg, 4)
                    else:
                        neutral_score = max(pos, neg, 0.5)
                        return 'neutral', round(neutral_score, 4)
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")

    return _rule_based_sentiment(text)

def analyze_category(text):
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(2 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
        score += sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    question_words = ['how', 'what', 'when', 'where', 'why', 'which', 'who', '?']
    if any(qw in text_lower.split() for qw in question_words) or '?' in text:
        return 'question'
    return 'complaint'

def analyze_priority(text):
    text_lower = text.lower()
    for level, keywords in PRIORITY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return level
    urgent_words = ['urgent', 'asap', 'immediately', 'emergency']
    angry_words = ['angry', 'furious', 'outraged', 'frustrated', 'terrible']
    for w in urgent_words:
        if w in text_lower:
            return 'high'
    for w in angry_words:
        if w in text_lower:
            return 'high'
    text_len = len(text.split())
    if text_len > 100:
        return 'medium'
    return 'low'

def extract_keywords(text):
    text_lower = text.lower()
    words = re.findall(r'[a-zA-Zа-яА-Я]{3,}', text_lower)
    words = [w for w in words if w not in STOPWORDS]
    if not words:
        return []
    common = Counter(words).most_common(8)
    return [w for w, c in common]

def generate_summary(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= 1:
        if len(text) > 150:
            return text[:147] + '...'
        return text
    scored = []
    for s in sentences:
        if len(s) < 10:
            continue
        s_lower = s.lower()
        score = 0
        for cat in CATEGORY_KEYWORDS.values():
            for kw in cat:
                if kw in s_lower:
                    score += 1
        if any(w in s_lower for w in ['urgent', 'important', 'critical', 'error', 'bug']):
            score += 2
        scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], -len(x[1])))
    if scored and scored[0][0] > 0:
        best = scored[0][1]
        if len(best) > 200:
            return best[:197] + '...'
        return best
    return sentences[0] if len(sentences[0]) < 200 else sentences[0][:197] + '...'

CATEGORY_LABELS_EN = {
    'complaint': 'complaint',
    'suggestion': 'suggestion',
    'question': 'question',
    'praise': 'praise',
    'bugreport': 'bugreport',
}

PRIORITY_LABELS_EN = {
    'low': 'low',
    'medium': 'medium',
    'high': 'high',
    'critical': 'critical',
}

def _rule_based_sentiment(text):
    text_lower = text.lower()
    positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
                      'love', 'best', 'perfect', 'happy', 'pleased', 'satisfied', 'thanks',
                      'helpful', 'awesome', 'brilliant', 'outstanding', 'superb', 'grateful']
    negative_words = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'disgusting',
                      'useless', 'poor', 'broken', 'damage', 'damaged', 'defective',
                      'disappointed', 'frustrating', 'annoying', 'angry', 'furious']
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    if pos_count > neg_count:
        score = 0.5 + (pos_count - neg_count) * 0.1
        return 'positive', round(min(score, 0.99), 4)
    elif neg_count > pos_count:
        score = 0.5 + (neg_count - pos_count) * 0.1
        return 'negative', round(min(score, 0.99), 4)
    else:
        return 'neutral', 0.5

def analyze_full(text):
    emotion, emotion_score = analyze_emotion(text)
    category = analyze_category(text)
    priority = analyze_priority(text)
    keywords = extract_keywords(text)
    summary = generate_summary(text)
    result = {
        'text': text,
        'emotion': emotion,
        'emotion_score': emotion_score,
        'category': category,
        'priority': priority,
        'keywords': keywords,
        'summary': summary,
    }
    result['sentiment'] = emotion
    result['sentiment_score'] = emotion_score
    result['complaint_category'] = category
    return result
