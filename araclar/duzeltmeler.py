# What the English and Arabic pages change besides the texts: the place of the files (one folder down), the language
# and direction of the page, the language switch, and the words in the page's script.
SW_TR = '<span class="langsw"><a href="./" aria-current="page">TR</a><a href="en/">EN</a><a href="ar/" lang="ar">عربي</a></span>'
SW = {'en': '<span class="langsw"><a href="../" hreflang="tr">TR</a><a href="./" aria-current="page">EN</a><a href="../ar/" lang="ar" hreflang="ar">عربي</a></span>',
      'ar': '<span class="langsw"><a href="../" hreflang="tr">TR</a><a href="../en/" hreflang="en">EN</a><a href="./" lang="ar" aria-current="page">عربي</a></span>'}
SCRIPT = {
 'en': [('"Windows 10 ve 11 · 64 bit"', '"Windows 10 and 11 · 64-bit"'), ('"Android 8.0 ve üstü"', '"Android 8.0 or later"'),
        ('"macOS · Apple Silicon (Intel için aşağıdaki bağlantı)"', '"macOS · Apple Silicon (Intel: link below)"'), ('"Linux · 64 bit"', '"Linux · 64-bit"'),
        ('"Windows için ücretsiz indir"', '"Free download for Windows"'), ('"Android için ücretsiz indir"', '"Free download for Android"'),
        ('"Mac için ücretsiz indir"', '"Free download for Mac"'), ('"Linux için ücretsiz indir"', '"Free download for Linux"'),
        ('"Ücretsiz indir"', '"Free download"'), ('"Sürüm "', '"Version "')],
 'ar': [('"Windows 10 ve 11 · 64 bit"', '"Windows 10 و11 · 64 بت"'), ('"Android 8.0 ve üstü"', '"Android 8.0 فما فوق"'),
        ('"macOS · Apple Silicon (Intel için aşağıdaki bağlantı)"', '"macOS · Apple Silicon (لـ Intel: الرابط أدناه)"'), ('"Linux · 64 bit"', '"Linux · 64 بت"'),
        ('"Windows için ücretsiz indir"', '"تنزيل مجاني لـ Windows"'), ('"Android için ücretsiz indir"', '"تنزيل مجاني لـ Android"'),
        ('"Mac için ücretsiz indir"', '"تنزيل مجاني لـ Mac"'), ('"Linux için ücretsiz indir"', '"تنزيل مجاني لـ Linux"'),
        ('"Ücretsiz indir"', '"تنزيل مجاني"'), ('"Sürüm "', '"الإصدار "')],
}
NOTE = {'en': '<p class="note">This is a translation; in case of any difference the Turkish text prevails.</p>',
        'ar': '<p class="note">هذا نص مترجم؛ وعند أي اختلاف يُعتمد النص التركي.</p>'}

LOCAL_SHOTS = ['ayet', 'mushaf', 'arama', 'hadis', 'serh', 'lugat', 'secere', 'ravi', 'dualar', 'takip']

def FIX(L):
    def f(page):
        r = [('<html lang="tr">', f'<html lang="{L}"' + (' dir="rtl"' if L == 'ar' else '') + '>'),
             ('href="img/', 'href="../img/'), ('src="img/', 'src="../img/'), ('poster="img/', 'poster="../img/'),
             ('content="img/', 'content="../img/'), ('src="tanitim.mp4"', 'src="../tanitim.mp4"'), ('href="tanitim.mp4"', 'href="../tanitim.mp4"'),
             ('href="./">', 'href="./">'), (SW_TR, SW[L])]
        if page == 'gizlilik.html':
            r += [('<span class="langsw"><a href="gizlilik.html" aria-current="page">TR</a><a href="en/gizlilik.html">EN</a><a href="ar/gizlilik.html" lang="ar">عربي</a></span>',
                   '<span class="langsw"><a href="../gizlilik.html" hreflang="tr">TR</a>' + ('<a href="gizlilik.html" aria-current="page">EN</a><a href="../ar/gizlilik.html" lang="ar">عربي</a>' if L == 'en' else '<a href="../en/gizlilik.html">EN</a><a href="gizlilik.html" lang="ar" aria-current="page">عربي</a>') + '</span>')]
        if page == 'index.html':
            r += SCRIPT[L]
            # the program's screenshots in the page's language (the others show the Turkish interface)
            r += [(f'src="../img/{n}.webp"', f'src="../img/{L}/{n}.webp"') for n in LOCAL_SHOTS]
            r += [('src="../img/dil-' + L + '.webp"', 'src="../img/dil-' + L + '.webp"')]
            r += [('<ol class="terms">', NOTE[L] + '<ol class="terms">')]
        return r
    return lambda page: f(page)
FIX = {L: FIX(L) for L in ('en', 'ar')}
