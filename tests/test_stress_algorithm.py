from stress_algorithm import calculate_stress_score, classify_stress

def test_low_stress_score():
    score = calculate_stress_score('great', 9, 1, 1, [1,1,1,1,1], 'I feel calm and focused')
    assert 0 <= score <= 39
    assert classify_stress(score) == 'Low Stress'

def test_high_stress_score():
    score = calculate_stress_score('anxious', 2, 10, 10, [5,5,5,5,5], 'I feel panic overwhelmed burnout')
    assert score >= 70
    assert classify_stress(score) == 'High Stress'
