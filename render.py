#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: set sw=4 ts=4 et:
#
# Release countdown banner generation script
# by Pascal Bleser <pascal.bleser@opensuse.org>
# and other openSUSE contributors

import sys
import datetime
import fileinput
from cairosvg import svg2png
from functools import reduce
from optparse import OptionParser
import os
import tempfile
import shutil
import atexit

# VERSION should be a release number or "conference" as in the following examples:
# VERSION = "13.2"
# VERSION = "conference"
VERSION = "16.0"

# UTC timestamp!
RELEASE = datetime.datetime(2025, 10, 1, 12, 0, 0)


VARIANTS = ["label", "nolabel"]

###--- no need to change below this line ---###

PREFIX = "opensuse-%s" % VERSION
# dimensions are tuples of (width,height,name)
sizes = [(600,100,"wide","wide"), (400,400,"large","square"), (256,256,"medium","square"), (130,130,"small","square")]
varlist = [""] + ["-%s" % (x) for x in VARIANTS]

options = None
optionParser = OptionParser(usage="%prog [options] [<output directory>]",
        description="render countdown image")
optionParser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='be verbose')
optionParser.add_option('-l', '--lang', action='append', dest='lang', default=[], help='language to render')
optionParser.add_option('-k', '--keep', action='store_true', dest='keep', default=False, help='keep SVG files')
optionParser.add_option('-s', '--size', action='append', dest='sizes', default=[], help='sizes to render')
optionParser.add_option('-d', '--days', dest='forced_days', type='int', default=None, help='force the amount of remaining days', metavar='DAYS')
(options, args) = optionParser.parse_args(sys.argv)

if len(options.sizes) == 0:
    options.sizes = [x[2] for x in sizes]

def msg_ru(n):
    if (n != 11) and (n % 10 == 1):
        pre = 'Остался'
    else:
        pre = 'Осталось'
    if n % 10 == 1 and n % 100 != 11:
        return pre, 'день'
    if n % 10 >= 2 and n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return pre, 'дня'
    return pre, 'дней'

def msg_sk(n):
    if n == 1:
        post = 'deň'
    elif n <= 4:
        post = 'dni'
    else:
        post = 'dní'
    return 'Už len', post

def msg_pl(n):
    if n == 1:
        post = 'godzinę'
    elif n <= 4:
        post = 'godziny'
    else:
        post = 'godzin'
    return 'Dostępne za', post

def msg_pl_days(n):
    if n == 1:
        # pre = 'Pozostał tylko'
        post = 'dzień'
    elif n <= 4:
        # pre = 'Pozostały tylko'
        post = 'dni'
    else:
        # pre = 'Pozostało tylko'
        post = 'dni'
    return 'Dostępne za', post

def msg_pl_conference(n):
    if n == 1:
        post = 'godzinę'
    elif n <= 4:
        post = 'godziny'
    else:
        post = 'godzin'
    return 'Zaczyna się za', post

def msg_lt(n):
    if (n % 10 == 1) and (n != 11):
        post = 'dienos'
    else:
        post = 'dienų'
    return 'Pasirodys po', post

if VERSION == "conference":
    avail = {
        'en': 'Join\nUs!',
        'de': ' Begleiten\nSie Uns !',
        'ca': 'Uneix-te\na nosaltres!',
        'sk': 'Pridajte sa!',
        'fr': 'Rejoignez-\nnous!',
        'uk': 'Приєднуйтеся!!',
        'ru': 'Присоединяйся!',
        'nl': 'Bezoek!',
        'es': '¡Únete a nosotros!',
        'it': 'Unisciti a noi!',
        'el': 'Ελάτε μαζί μας!',
        'pl': 'Dołącz\ndo nas!',
        'pt': 'Junte-se a nós!',
        'pt_BR': 'Junte-se a nós!',
        'ja': 'ご参加ください！',
        'da': 'Vær\nmed!',
        'nb': 'Bli\nmed!',
        'nn': 'Bli\nmed!',
        'lt': 'Dalyvaukite!',
        'zh': '加入我们！',
         }

    almost = {
        'en': ['Starts in', ['hours!', 'hour!']],
        'ca': ['Comença d\'aquí a', ['hores!', 'hora!']],
        'nl': ['Begint over', ['uren!', 'uur']],
        'fr': ['Débute dans', ['heures!', 'heure!']],
        'de': ['in', ['Stunden!', 'Stunde!']],
        'it': ['Comincia tra', ['ore!', 'ora!']],
        'uk': ['Розпочнеться через', ['годин!', 'годину!']],
        'ru': ['Начнётся через', ['часов!', 'час!']],
        'pt': ['Começa em', ['horas!', 'hora!']],
        'pt_BR': ['Começa em', ['horas!', 'hora!']],
        'el': ['Ξεκινά σε', ['ώρα!', 'ώρες!']],
        'es': ['¡Empieza en', ['horas!', 'hora!']],
        'ja': ['あと [N 時間] で始まります', ['あと [N 日] で始まりま', 'に始 まります']],
        'da': ['Begynder om ', ['timer!', 'time!']],
        'nb': ['Begynner om', ['timer!', 'time!']],
        'nn': ['Begynner om', ['timar!', 'time!']],
        'lt': ['Prasidės po', ['val.!', 'val.!']],
        'zh': ['将在', ['小时后开始！', '小时后开始！']],
        'pl': msg_pl_conference,
         }
else:
    avail = {
        'en': 'Out\nnow!',
        'de': 'Jetzt\nverfügbar!',
        'cs': 'Nyní\ndostupné!',
        'sk': 'Stahuj\nteraz!',
        'fr': 'Disponible\nmaintenant!',
        'da': 'Ude\nnu!',
        'ru': 'Уже\nвышла',
        'nl': 'Nu\nbeschikbaar!',
        'fi': 'Nyt\nsaatavissa!',
        'es': '¡Ya\ndisponible!',
        'it': 'Disponibile\nora!',
        'el': 'Διαθέσιμο\nτώρα!',
        'sv': 'Ute\nnu!',
        'hr': 'Sad\ndostupan!',
        'nb': 'Ute\nnå!',
        'pt': 'Já\ndisponível!',
        'pt_BR': 'Baixe\nagora!',
        'hu': 'Megjelent',
        'ro': 'Disponibil\nacum!',
        'si': 'Zunaj\nZdaj!',
        'tw': '盛裝發佈！',
        'id': 'Download\nsekarang',
        'bg': 'довнлоад\nсега!',
        'ja': '好評\n提供中！',
        'wa': 'Disponibe\ndo côp!',
        'gl': 'Xa está\ndispoñible!',
        'ge': 'არსებული',
        'lt': 'Išleista!',
        'tr': 'Çıktı!',
        'zh': '现已发布！',
        'pl': 'Dostępne\nteraz!',
        'af': 'Nou\nbeskikbaar!'
        }

    almost = {
        'en': ['Release in', ['hours!', 'hour!']],
        'tw': ['即刻登場', ['小時！', '小時！']],
        'fr': ['Plus que', ['heures!', 'heure!']],
        'de': ['Verfügbar in', ['Stunden!', 'Stunde!']],
        'it': ['Disponibile in', ['ore!', 'ora!']],
        'da': ['Udgives om', ['timer!', 'time!']],
        'es': ['¡Disponible en', ['horas!', 'hora!']],
        'pt': ['Disponível em', ['horas!', 'hora!']],
        'pt_BR': ['Disponível em', ['horas!', 'hora!']],
        'lt': ['Pasirodys po', ['val.', 'val.']],
        'tr': ['', ['saat sonra burada!', 'saat sonra burada!']],
        'zh': ['', ['小时后发布！', '小时后发布！']],
        'af': ['Net', ['uur bly!', 'ure bly!']],
#        'pl': msg_pl,
        }

m = {
        'en': ['Only', 'days to go', '', 'day to go'],
        'de': ['Nur noch', 'Tage', 'Nur noch', 'Tag'],
        'cs': ['', 'dní do vydání'],
        'sk': msg_sk,
        'fr': ['Plus que', 'jours', "Plus qu'", 'jour'],
        'da': ['', 'dage tilbage'],
        'ru': msg_ru,
        'nl': ['Nog', 'dagen', 'Nog', 'dag'],
        'fi': ['', 'päivää\njäljellä'],
        'es': ['Quedan', 'días', 'Queda', 'día'],
        'it': ['', 'giorni al via', '', 'giorno al via'],
        #'el': ['', 'περισσότερες\nμέρες', 'Τελευταία|Μέρα'],
        'el': ['Μόνο', 'μέρες ακόμη'],
        'sv': ['', 'dagar kvar'],
        'hr': ['Još', 'dana'],
        'nb': ['', 'dager igjen'],
        'pt': ['Faltam', 'dias', 'Falta', 'dia'],
        'pt_BR': ['Faltam', 'dias', 'Falta', 'dia'],
        'hu': ['Még', 'nap'],
        'ro': ['Încă', 'zile'],
        'id': ['', 'hari lagi'],
        'bg': ['още', 'дин', 'още', 'ден'],
        'ja': ['いよいよ登場！\nあと', '日'],
        'wa': ['Co', 'djoûs a\nratinde', 'Co', 'djoû a ratinde'],
        'tw': ['倒數', '天'],
        'gl': ['Dispoñible en', 'días', 'Dispoñible en', 'día'],
        'lt': msg_lt,
        'tr': ['', 'gün kaldı'],
        'zh': ['仅剩', '天'],
        'pl': msg_pl_days,
        'af': ['Net', 'dae bly', 'Net', 'dag bly'],
}

extra = {
        'tr': {
            'Linux for open minds': 'Açık fikirliler için linux',
        },
        'zh': {
            'Linux for open minds': 'Linux 献给开放的思想',
        },
}

# when adding or changing fonts, please mail admin@o.o to ensure these fonts get installed on the server
font_override = {
        'tw': 'Noto Sans TC',
        'ja': 'Noto Sans JP',
        'cn': "Noto Sans SC",
        'zh': 'Noto Sans SC',
        'kr': 'Noto Sans KR',
        }

font_to_replace = 'Source Sans Pro'
default_font = 'Source Sans Pro'

if len(args) >= 2:
    outdir = args[1]
else:
    outdir = "../output/%s" % VERSION

if len(options.lang) > 0:
    languages = options.lang
else:
    languages = list(m.keys()) + list(avail.keys())

if options.forced_days is not None:
    days = options.forced_days
    seconds = 0
else:
    diff = RELEASE - datetime.datetime.utcnow()
    days = diff.days
    seconds = diff.seconds

workdir = None

def on_exit():
    if workdir is not None and os.path.exists(workdir):
        shutil.rmtree(workdir)

atexit.register(on_exit)

workdir = tempfile.mkdtemp(prefix='countdown', suffix='tmp')
dev_null = open('/dev/null', 'w')

def sjoin(a, sep, b):
    r = a
    if len(a) > 0 and len(b) > 0:
        r += sep
    r += b
    return r

def render(lang, truelang, top1, top2, center, bottom1, bottom2, template_variant=None):
    x = str(center).encode('ascii', 'xmlcharrefreplace')
    y = str(top1).encode('ascii', 'xmlcharrefreplace')
    yy = str(top2).encode('ascii', 'xmlcharrefreplace')
    z = str(bottom1).encode('ascii', 'xmlcharrefreplace')
    zz = str(bottom2).encode('ascii', 'xmlcharrefreplace')
    ly = reduce(lambda x,y: sjoin(x, " ".encode('ascii'), y), [y, yy])
    lz = reduce(lambda x,y: sjoin(x, " ".encode('ascii'), y), [z, zz])

    font_repl = font_override.get(truelang, default_font)

    for size in sizes:
        if not size[2] in options.sizes:
            continue

        if y is not None and len(y) > 0:
            t = "-top"
        else:
            t = None

        for var in varlist:
            if template_variant is None:
                if t is not None:
                    template = "%s%s%s.svg" % (size[3], var, t)
                if t is None or not os.path.exists(template):
                    template = "%s%s.svg" % (size[3], var)
            else:
                if t is not None:
                    template = "%s%s%s-%s.svg" % (size[3], var, t, template_variant)
                if t is None or not os.path.exists(template):
                    template = "%s%s-%s.svg" % (size[3], var, template_variant)

            if not os.path.exists(template):
                if options.verbose:
                    print("skipping %s / %s / %s: template \"%s\" does not exist" % (lang, var, size[2], template))
                if var:
                    print("Needed template \"%s\" is missing. Aborting" % (template), file=sys.stderr)
                    sys.exit(1)
                continue

            outfile = "%s/%s%s.%s.png" % (outdir, size[2], var, lang)

            if options.verbose:
                print("%s / %s / %s: %s -> %s" % (lang, var, size[2], template, outfile))

            workfile = os.path.join(workdir, "work.svg")
            with open(workfile, "wb") as out:
                for line in fileinput.FileInput(template, mode="rb"):
                    line = line.replace(b"@@", x).replace(b"@TOPC@", y).replace(b"@TOP@", yy).replace(b"@BOTTOM@", z).replace(b"@BOTTOMC@", zz)
                    line = line.replace(b"@_TOP_@", ly).replace(b"@_BOTTOM_@", lz)
                    line = line.replace(b"##.#", VERSION.encode('ascii', 'xmlcharrefreplace'))

                    if lang in extra:
                        for s, r in extra[lang].items():
                            line = line.replace(s.encode('ascii', 'xmlcharrefreplace'), str(r).encode('ascii', 'xmlcharrefreplace'))

                    if font_repl is not None:
                        line = line.replace(font_to_replace.encode('ascii', 'xmlcharrefreplace'), font_repl.encode('ascii', 'xmlcharrefreplace'))

                    out.write(line)

            svg2png(url=workfile, write_to=outfile, output_width=size[0], output_height=size[1])
            if options.keep:
                svg_outfile = "%s/%s%s.%s.svg" % (outdir, size[3], var, lang)
                shutil.copyfile(workfile, svg_outfile)
                if options.verbose:
                    print("SVG saved as %s" % svg_outfile)

if options.verbose:
    print("days: %d" % (days))

if not os.path.exists(outdir):
    os.makedirs(outdir)

if days == 0 and seconds > 0:
    for lang in languages:
        hours = (seconds / 3600) + 1
        text = "%02d" % (hours)
        post2 = ""

        if lang in almost:
            m = almost[lang]
            truelang = lang
        else:
            m = almost['en']
            truelang = 'en'

        top = m[0]
        if hours > 1:
            post = m[1][0]
        else:
            post = m[1][1]

        render(lang, truelang, "", top, text, post, post2)

elif days <= 0:
    for lang in languages:
        if not lang in languages:
            continue

        if avail.get(lang):
            text = avail[lang]
        else:
            text = avail['en']

        if lang in almost:
            m = almost[lang]
            truelang = lang
        else:
            m = almost['en']
            truelang = 'en'

        parts = text.split("\n")
        if len(parts) == 1:
            render(lang, truelang, None, parts[0], None, "", None, "outnow")
        else:
            render(lang, truelang, None, parts[0], None, parts[1], None, "outnow")
else:
    for lang, msg in m.items():
        if not lang in languages:
            continue
        whole = None
        text = str(days)
        post2 = ''
        pre0 = ''

        if callable(msg):
            pre, post = msg.__call__(days)
        elif len(msg) == 4:
            if days > 1:
                pre = msg[0]
                post = msg[1]
            else:
                pre = msg[2]
                post = msg[3]
        elif len(msg) == 2:
            pre = msg[0]
            post = msg[1]
        elif len(msg) == 3:
            if days > 1:
                pre = msg[0]
                post = msg[1]
            else:
                pre = None
                post = None
                text = None
                whole = msg[2]
        else:
            print("unsupported msg: %s" % msg, file=sys.stderr)
            sys.exit(1)

        if post is not None and "\n" in post:
            parts = post.split("\n")
            post = parts[0]
            post2 = parts[1]

        if pre is not None and "\n" in pre:
            parts = pre.split("\n")
            pre0 = parts[0]
            pre = parts[1]

        if lang in almost:
            m = almost[lang]
            truelang = lang
        else:
            m = almost['en']
            truelang = 'en'

        render(lang, truelang, pre0, pre, text, post, post2)
