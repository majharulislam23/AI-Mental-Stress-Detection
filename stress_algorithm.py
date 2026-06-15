NEGATIVE_KEYWORDS = {
    'overwhelmed': 8, 'anxious': 8, 'panic': 12, 'tired': 5, 'exhausted': 9,
    'sad': 6, 'hopeless': 12, 'angry': 6, 'pressure': 6, 'deadline': 5,
    'insomnia': 8, 'crying': 8, 'fear': 7, 'burnout': 12, 'lonely': 7,
    'stress': 6, 'worried': 6, 'restless': 6, 'unsafe': 15
}
POSITIVE_KEYWORDS = {
    'calm': -5, 'happy': -5, 'relaxed': -6, 'confident': -4,
    'peaceful': -6, 'better': -3, 'focused': -3, 'hopeful': -4
}
MOOD_WEIGHTS = {'great': 4, 'good': 12, 'okay': 24, 'sad': 40, 'anxious': 48, 'angry': 42}

QUESTIONS = [
    'I feel overwhelmed by my daily tasks.',
    'I have trouble sleeping.',
    'I feel anxious or restless.',
    'I find it difficult to concentrate.',
    'I feel emotionally exhausted.'
]

def text_sentiment_score(text: str) -> int:
    if not text:
        return 0
    lowered = text.lower()
    score = 0
    for word, value in NEGATIVE_KEYWORDS.items():
        if word in lowered:
            score += value
    for word, value in POSITIVE_KEYWORDS.items():
        if word in lowered:
            score += value
    return max(-15, min(25, score))

def classify_stress(score: int) -> str:
    if score <= 39:
        return 'Low Stress'
    if score <= 69:
        return 'Moderate Stress'
    return 'High Stress'

def calculate_stress_score(mood, sleep_quality, pressure_level, anxiety_level, questionnaire_values=None, feeling_text=''):
    questionnaire_values = questionnaire_values or []
    mood_component = MOOD_WEIGHTS.get(str(mood).lower(), 24)
    sleep_component = (10 - int(sleep_quality)) * 3
    pressure_component = int(pressure_level) * 3
    anxiety_component = int(anxiety_level) * 3
    questionnaire_component = sum(int(v) for v in questionnaire_values) * 2
    text_component = text_sentiment_score(feeling_text)
    raw_score = mood_component + sleep_component + pressure_component + anxiety_component + questionnaire_component + text_component
    return max(0, min(100, round(raw_score)))

def generate_insights(score, mood, sleep_quality, pressure_level, anxiety_level, questionnaire_values=None, feeling_text=''):
    level = classify_stress(score)
    factors = []
    recommendations = []

    if int(sleep_quality) <= 5:
        factors.append('Reduced sleep quality')
        recommendations.append('Follow a consistent sleep routine and avoid screens 30 minutes before bed.')
    if int(pressure_level) >= 7:
        factors.append('High work or study pressure')
        recommendations.append('Break large tasks into 25-minute focus blocks with short recovery breaks.')
    if int(anxiety_level) >= 7:
        factors.append('Elevated anxiety or restlessness')
        recommendations.append('Try slow breathing: inhale for 4 seconds, hold for 4, exhale for 6.')
    if str(mood).lower() in ['sad', 'anxious', 'angry']:
        factors.append(f'Current mood: {mood}')
        recommendations.append('Talk with a trusted person and write down what is causing the strongest emotion.')
    if text_sentiment_score(feeling_text) > 8:
        factors.append('Stress-related words detected in your text')
        recommendations.append('Use journaling to separate facts, feelings, and next small actions.')

    if not factors:
        factors.append('No major risk factor detected')
        recommendations.append('Maintain your current routine with regular sleep, movement, and hydration.')

    if level == 'Low Stress':
        explanation = 'Your current inputs suggest a stable emotional state with manageable pressure.'
    elif level == 'Moderate Stress':
        explanation = 'Your current pattern suggests noticeable stress. Early self-care and workload adjustments may help.'
    else:
        explanation = 'Your current pattern suggests high stress. Consider immediate rest, support from trusted people, or professional help if this continues.'
        recommendations.append('If you feel unsafe or unable to cope, use the emergency support page or contact local emergency services.')

    return {
        'level': level,
        'explanation': explanation,
        'factors': factors,
        'recommendations': recommendations
    }

def chatbot_reply(message: str) -> str:
    text = (message or '').lower()
    if any(word in text for word in ['unsafe', 'harm', 'suicide', 'kill myself', 'end my life']):
        return 'I am sorry you are feeling this way. Please contact emergency services or a trusted person immediately. You deserve immediate support.'
    if any(word in text for word in ['sleep', 'insomnia', 'tired']):
        return 'Sleep problems can increase stress. Try a quiet wind-down routine, reduce caffeine late in the day, and keep a regular sleep time.'
    if any(word in text for word in ['exam', 'study', 'deadline', 'work']):
        return 'For pressure from study or work, choose one small task, set a 25-minute timer, and take a 5-minute break after finishing.'
    if any(word in text for word in ['anxious', 'panic', 'worried']):
        return 'Try grounding yourself: name 5 things you see, 4 things you feel, 3 things you hear, 2 things you smell, and 1 thing you taste.'
    return 'Thank you for sharing. A helpful next step is to pause, breathe slowly, drink water, and identify one small action you can take right now.'
