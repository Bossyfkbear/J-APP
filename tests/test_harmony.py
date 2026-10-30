from apt.harmony import romanize

def test_major():
    assert romanize('C','C major')=='I'
    assert romanize('G7','C major')=='V7'
    assert romanize('Am','C major')=='vi'
    assert romanize('F','C major')=='IV'

def test_minor():
    assert romanize('Am','A minor')=='i'
    assert romanize('F','A minor')=='VI'

def test_chromatic():
    assert romanize('C#','C major').startswith('chromatic')
