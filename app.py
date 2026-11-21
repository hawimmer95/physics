"""Physik-Trainer – interaktive Lernhilfe für die Physik-Schularbeit (ca. 2. Klasse / 12 Jahre).

Start:  streamlit run app.py
"""

import math
import random

import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Physik-Trainer", page_icon="", layout="wide")

G_MOND = 1.62
SCHALL = 340  # m/s

BLAU = "#1f77b4"
ROT = "#d62728"
GRUEN = "#2ca02c"
ORANGE = "#ff7f0e"


# =====================================================================
# Hilfsfunktionen
# =====================================================================
def de(x, nd=2):
    """Zahl österreichisch/deutsch formatieren (Komma, keine unnötigen Nullen)."""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    s = f"{x:.{nd}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def tx(x, nd=2):
    """Zahl für LaTeX (Komma ohne Abstand)."""
    return de(x, nd).replace(",", "{,}")


def q(x, einheit, nd=2):
    """Größe mit Einheit als LaTeX, z.B. q(9.81, 'm/s²')."""
    if einheit.endswith("²"):
        return tx(x, nd) + r"\,\text{" + einheit[:-1] + "}^2"
    return tx(x, nd) + r"\,\text{" + einheit + "}"


def frac(a, b):
    return r"\frac{" + a + "}{" + b + "}"


def weg(gegeben, gesucht, schritte, antwort, merke=None):
    """Lösungsweg im Schulformat: Gegeben – Gesucht – Formel – Einsetzen – Ergebnis."""
    zeilen = [f"**Gegeben:** {gegeben}", f"**Gesucht:** {gesucht}"]
    for label, latex in schritte:
        zeilen.append(f"**{label}:** ${latex}$")
    zeilen.append(f"**Antwort:** {antwort}")
    if merke:
        zeilen.append(f"{merke}")
    return "  \n".join(zeilen)


def lies_zahl(text):
    if text is None:
        return None
    text = text.strip().replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def layout(fig, xt, yt, hoehe=320, titel=None):
    fig.update_layout(
        height=hoehe,
        margin=dict(l=10, r=10, t=45 if titel else 20, b=10),
        xaxis_title=xt,
        yaxis_title=yt,
        title=titel,
        legend=dict(orientation="h", y=1.15, x=0),
    )
    return fig


def zeige(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def einfach(md, titel="Einfach erklärt – ganz ohne Formeln"):
    """Anschauliche Erklärung mit Alltagsbildern, bevor die Mathematik kommt."""
    with st.container(border=True):
        st.markdown(f"### {titel}")
        st.markdown(md)


def bauchgefuehl(md):
    """Schätz-Regeln, mit denen man prüfen kann, ob ein Ergebnis Sinn ergibt."""
    st.info("**Bauchgefühl-Check – kann mein Ergebnis stimmen?**\n\n" + md)


# ---------------------------------------------------------------------
# Übungsaufgaben mit Prüfen-Knopf und Lösungsweg
# ---------------------------------------------------------------------
def neue_aufgabe(key, gen):
    # Jede Aufgabe bekommt eine neue Nummer -> frisches Eingabefeld.
    # (Nur den Key zu löschen reicht nicht: der Browser behält sonst den alten
    # Text, und der wird dann gegen die neue Aufgabe geprüft.)
    alt = st.session_state.get(key)
    nr = alt.get("nr", 0) + 1 if alt else 0
    if alt:
        st.session_state.pop(f"{key}_ans_{alt.get('nr', 0)}", None)
    task = gen()
    task["nr"] = nr
    st.session_state[key] = task
    st.session_state[key + "_status"] = None


def aufgabe(key, gen, titel="Übungsaufgabe"):
    if key not in st.session_state:
        neue_aufgabe(key, gen)
    task = st.session_state[key]
    ans_key = f"{key}_ans_{task.get('nr', 0)}"
    with st.container(border=True):
        st.markdown(f"#### {titel}")
        st.markdown(task["text"])
        if task.get("fig") is not None:
            zeige(task["fig"])
        st.text_input(
            f"Deine Antwort (in {task['unit']})",
            key=ans_key,
            placeholder="z.B. 12,5",
        )
        c1, c2, _ = st.columns([1, 1, 2])
        if c1.button("Prüfen", key=key + "_chk", width="stretch"):
            wert = lies_zahl(st.session_state.get(ans_key))
            if wert is None:
                st.session_state[key + "_status"] = "leer"
            else:
                soll = task["answer"]
                tol = task.get("tol", max(0.03 * abs(soll), 0.02))
                richtig = abs(wert - soll) <= tol
                st.session_state[key + "_status"] = "richtig" if richtig else "falsch"
                if not task.get("gezaehlt"):
                    task["gezaehlt"] = True
                    st.session_state.versuche += 1
                    st.session_state.punkte += int(richtig)
        c2.button("Neue Aufgabe", key=key + "_neu", on_click=neue_aufgabe,
                  args=(key, gen), width="stretch")

        status = st.session_state.get(key + "_status")
        if status == "leer":
            st.warning("Bitte gib zuerst eine Zahl ein.")
        elif status == "richtig":
            st.success(f"Richtig. ({de(task['answer'])} {task['unit']})")
        elif status == "falsch":
            st.error("Stimmt nicht ganz. Check den Lösungsweg oder versuch's nochmal.")

        with st.expander("Lösungsweg anzeigen"):
            st.markdown(task["solution"])


def quiz(key, fragen):
    """Multiple-Choice-Quiz. fragen = Liste von (Frage, [Optionen], Index richtig, Erklärung)."""
    with st.container(border=True):
        st.markdown("#### Verständnis-Quiz")
        with st.form(key):
            antworten = []
            for i, (frage, optionen, _, _) in enumerate(fragen):
                antworten.append(st.radio(f"**{i + 1}. {frage}**", optionen, index=None,
                                          key=f"{key}_{i}"))
            abgeschickt = st.form_submit_button("Auswerten")
        if abgeschickt:
            punkte = 0
            for i, ((frage, optionen, richtig, erkl), a) in enumerate(zip(fragen, antworten)):
                if a == optionen[richtig]:
                    punkte += 1
                    st.success(f"**{i + 1}.** Richtig! {erkl}")
                elif a is None:
                    st.warning(f"**{i + 1}.** Nicht beantwortet. Richtig wäre: *{optionen[richtig]}*. {erkl}")
                else:
                    st.error(f"**{i + 1}.** Leider falsch. Richtig ist: *{optionen[richtig]}*. {erkl}")
            st.markdown(f"### Ergebnis: {punkte} von {len(fragen)} richtig")
            if punkte == len(fragen):
                st.balloons()


# =====================================================================
# Aufgaben-Generatoren
# =====================================================================
WER_V = [("Ein Läufer", 3, 7), ("Eine Radfahrerin", 4, 10), ("Ein Auto", 10, 30),
         ("Ein Zug", 20, 40), ("Ein Hund", 5, 12)]


def gen_geschwindigkeit(g=None):
    wer, lo, hi = random.choice(WER_V)
    art = random.choice(["v", "s", "t", "kmh"])
    if art == "v":
        v = random.randint(lo, hi)
        t = random.choice([5, 10, 20, 30, 50, 60])
        s = v * t
        return dict(
            text=f"{wer} legt **{s} m** in **{t} s** zurück. Wie groß ist die Geschwindigkeit in m/s?",
            answer=v, unit="m/s",
            solution=weg(f"$s = {q(s, 'm')}$, $t = {q(t, 's')}$", "$v$ in m/s",
                         [("Formel", r"v = \frac{s}{t}"),
                          ("Einsetzen", "v = " + frac(q(s, "m"), q(t, "s"))),
                          ("Ergebnis", "v = " + q(v, "m/s"))],
                         f"Die Geschwindigkeit beträgt **{v} m/s** (= {de(v * 3.6, 1)} km/h)."))
    if art == "s":
        v = random.randint(lo, hi)
        t = random.choice([4, 8, 10, 15, 20, 30])
        s = v * t
        return dict(
            text=f"{wer} bewegt sich gleichförmig mit **{v} m/s**. Welchen Weg legt er/sie in **{t} s** zurück?",
            answer=s, unit="m",
            solution=weg(f"$v = {q(v, 'm/s')}$, $t = {q(t, 's')}$", "$s$ in m",
                         [("Formel (umgeformt)", r"v = \frac{s}{t} \;\Rightarrow\; s = v \cdot t"),
                          ("Einsetzen", "s = " + q(v, "m/s") + r" \cdot " + q(t, "s")),
                          ("Ergebnis", "s = " + q(s, "m"))],
                         f"Es werden **{s} m** zurückgelegt.",
                         "Formel-Dreieck: s oben, v und t unten. Zuhalten, was gesucht ist!"))
    if art == "t":
        v = random.randint(lo, hi)
        t = random.choice([5, 10, 12, 20, 25, 40])
        s = v * t
        return dict(
            text=f"{wer} bewegt sich mit **{v} m/s**. Wie lange braucht er/sie für **{s} m**?",
            answer=t, unit="s",
            solution=weg(f"$v = {q(v, 'm/s')}$, $s = {q(s, 'm')}$", "$t$ in s",
                         [("Formel (umgeformt)", r"t = \frac{s}{v}"),
                          ("Einsetzen", "t = " + frac(q(s, "m"), q(v, "m/s"))),
                          ("Ergebnis", "t = " + q(t, "s"))],
                         f"Es dauert **{t} s**."))
    # km und Minuten -> km/h
    v = random.choice([12, 15, 18, 20, 24, 30, 36])
    tmin = random.choice([10, 15, 20, 30, 40])
    s = v * tmin / 60
    return dict(
        text=f"Eine Radfahrerin fährt **{de(s)} km** in **{tmin} Minuten**. Wie schnell ist sie in km/h?",
        answer=v, unit="km/h",
        solution=weg(f"$s = {q(s, 'km')}$, $t = {tmin}\\,\\text{{min}}$", "$v$ in km/h",
                     [("Zeit in Stunden umrechnen", f"t = {tmin}\\,\\text{{min}} = " + frac(str(tmin), "60")
                       + r"\,\text{h} = " + q(tmin / 60, "h", 3)),
                      ("Formel", r"v = \frac{s}{t}"),
                      ("Einsetzen", "v = " + frac(q(s, "km"), q(tmin / 60, "h", 3))),
                      ("Ergebnis", "v = " + q(v, "km/h"))],
                     f"Sie fährt **{v} km/h**.",
                     "Tipp: In 60 min fährt sie " + de(60 / tmin) + "-mal so weit wie in "
                     + str(tmin) + f" min, also {de(s)} · {de(60 / tmin)} = {v} km in einer Stunde."))


def gen_umrechnen(g=None):
    if random.random() < 0.5:
        v = random.choice([2, 3, 5, 10, 12, 15, 20, 25, 30])
        return dict(
            text=f"Rechne **{v} m/s** in **km/h** um.",
            answer=v * 3.6, unit="km/h",
            solution=weg(f"$v = {q(v, 'm/s')}$", "$v$ in km/h",
                         [("Regel", r"\text{m/s} \xrightarrow{\;\cdot 3{,}6\;} \text{km/h}"),
                          ("Rechnung", f"{v} \\cdot 3{{,}}6 = {tx(v * 3.6)}")],
                         f"**{v} m/s = {de(v * 3.6)} km/h**",
                         "Von m/s zu km/h wird die Zahl GRÖSSER → mal 3,6."))
    kmh = random.choice([18, 36, 54, 72, 90, 108, 126, 144, 9, 27])
    return dict(
        text=f"Rechne **{kmh} km/h** in **m/s** um.",
        answer=kmh / 3.6, unit="m/s",
        solution=weg(f"$v = {q(kmh, 'km/h')}$", "$v$ in m/s",
                     [("Regel", r"\text{km/h} \xrightarrow{\;: 3{,}6\;} \text{m/s}"),
                      ("Rechnung", f"{kmh} : 3{{,}}6 = {tx(kmh / 3.6)}")],
                     f"**{kmh} km/h = {de(kmh / 3.6)} m/s**",
                     "Von km/h zu m/s wird die Zahl KLEINER → durch 3,6."))


def gen_beschleunigung(g=None):
    art = random.choice(["v", "s", "a"])
    a = random.choice([1, 2, 3, 4, 5])
    t = random.choice([2, 3, 4, 5, 6, 8, 10])
    if art == "v":
        v = a * t
        return dict(
            text=f"Ein Auto fährt aus dem Stand los und beschleunigt gleichmäßig mit **a = {a} m/s²**. "
                 f"Wie schnell ist es nach **{t} s** (in m/s)?",
            answer=v, unit="m/s",
            solution=weg(f"$a = {q(a, 'm/s²')}$, $t = {q(t, 's')}$", "$v$",
                         [("Formel", r"v = a \cdot t"),
                          ("Einsetzen", "v = " + q(a, "m/s²") + r" \cdot " + q(t, "s")),
                          ("Ergebnis", "v = " + q(v, "m/s"))],
                         f"Nach {t} s fährt es **{v} m/s** (= {de(v * 3.6, 1)} km/h).",
                         f"a = {a} m/s² heißt: jede Sekunde wird es um {a} m/s schneller."))
    if art == "s":
        s = a * t * t / 2
        return dict(
            text=f"Ein Motorrad beschleunigt aus dem Stand mit **a = {a} m/s²**. "
                 f"Welchen Weg legt es in den ersten **{t} s** zurück?",
            answer=s, unit="m",
            solution=weg(f"$a = {q(a, 'm/s²')}$, $t = {q(t, 's')}$", "$s$",
                         [("Formel", r"s = \frac{a \cdot t^2}{2}"),
                          ("Einsetzen", "s = " + frac(q(a, "m/s²") + r" \cdot (" + q(t, "s") + ")^2", "2")),
                          ("Rechnen", "s = " + frac(f"{a} \\cdot {t * t}", "2") + r"\,\text{m}"),
                          ("Ergebnis", "s = " + q(s, "m"))],
                         f"Es legt **{de(s)} m** zurück.",
                         "Achtung: Zuerst t² ausrechnen (t mal t), dann mal a, dann durch 2!"))
    v = a * t
    return dict(
        text=f"Ein Zug fährt an und ist nach **{t} s** genau **{v} m/s** schnell. "
             f"Wie groß ist seine Beschleunigung?",
        answer=a, unit="m/s²",
        solution=weg(f"$v = {q(v, 'm/s')}$, $t = {q(t, 's')}$", "$a$",
                     [("Formel (umgeformt)", r"v = a \cdot t \;\Rightarrow\; a = \frac{v}{t}"),
                      ("Einsetzen", "a = " + frac(q(v, "m/s"), q(t, "s"))),
                      ("Ergebnis", "a = " + q(a, "m/s²"))],
                     f"Die Beschleunigung beträgt **{a} m/s²**."))


def gen_diagramm(g=None):
    v = random.choice([1, 2, 3, 4, 5, 6, 8, 10])
    t = np.arange(0, 11)
    fig = go.Figure(go.Scatter(x=t, y=v * t, mode="lines+markers", line=dict(color=BLAU, width=3)))
    layout(fig, "Zeit t in s", "Weg s in m", 300, "s-t-Diagramm")
    fig.update_xaxes(dtick=1)
    tp = random.choice([2, 4, 5, 10])
    return dict(
        text="Ein Körper bewegt sich gleichförmig. Lies aus dem **s-t-Diagramm** ab: "
             "Wie groß ist seine Geschwindigkeit?",
        fig=fig, answer=v, unit="m/s",
        solution=weg("das Diagramm", "$v$",
                     [("Punkt ablesen", f"t = {q(tp, 's')} \\;\\rightarrow\\; s = {q(v * tp, 'm')}"),
                      ("Formel", r"v = \frac{s}{t}"),
                      ("Einsetzen", "v = " + frac(q(v * tp, "m"), q(tp, "s"))),
                      ("Ergebnis", "v = " + q(v, "m/s"))],
                     f"Die Geschwindigkeit ist **{v} m/s**.",
                     "Such dir einen Punkt, der genau auf einer Gitterlinie liegt – dann ist das Ablesen leicht."))


MASSE_FAKTOR = {"t": 1_000_000, "kg": 1000, "dag": 10, "g": 1}


def gen_masse(g=None):
    paare = [("kg", "dag"), ("kg", "g"), ("dag", "g"), ("g", "dag"), ("dag", "kg"),
             ("g", "kg"), ("t", "kg"), ("kg", "t")]
    von, nach = random.choice(paare)
    if von == "t" or nach == "t":
        gramm = random.choice([500, 1200, 2500, 750, 3000, 40, 1500]) * 1000
    else:
        gramm = random.choice([10, 30, 50, 120, 250, 340, 500, 750, 1200, 2500, 4500, 3050, 80])
    wert = gramm / MASSE_FAKTOR[von]
    ergebnis = gramm / MASSE_FAKTOR[nach]
    f = MASSE_FAKTOR[von] / MASSE_FAKTOR[nach]
    if f > 1:
        regel = f"{von} ist die größere Einheit → in die kleinere Einheit {nach}: **mal {de(f)}**"
        rechnung = f"{tx(wert, 4)} \\cdot {tx(f)} = {tx(ergebnis, 4)}"
    else:
        regel = f"{von} ist die kleinere Einheit → in die größere Einheit {nach}: **durch {de(1 / f)}**"
        rechnung = f"{tx(wert, 4)} : {tx(1 / f)} = {tx(ergebnis, 4)}"
    return dict(
        text=f"Rechne **{de(wert, 4)} {von}** in **{nach}** um.",
        answer=ergebnis, unit=nach, tol=max(abs(ergebnis) * 0.001, 1e-6),
        solution=weg(f"{de(wert, 4)} {von}", f"Wert in {nach}",
                     [("Rechnung", rechnung)],
                     f"**{de(wert, 4)} {von} = {de(ergebnis, 4)} {nach}**",
                     regel + ".  Merke: 1 t = 1000 kg, 1 kg = 100 dag, 1 dag = 10 g."))


def gen_gewicht(g):
    art = random.choice(["erde", "mond", "rueck", "trick"])
    wer, m = random.choice([("Ein Schüler", 45), ("Eine Lehrerin", 60), ("Ein Hund", 20),
                            ("Ein Astronaut mit Raumanzug", 150), ("Ein Fahrrad", 12),
                            ("Eine Schultasche", 8), ("Ein Mann", 80)])
    if art == "erde":
        F = m * g
        return dict(
            text=f"{wer} hat eine Masse von **{m} kg**. Wie groß ist die Gewichtskraft auf der **Erde**?",
            answer=F, unit="N",
            solution=weg(f"$m = {q(m, 'kg')}$, $g = {q(g, 'N/kg')}$", r"$F_G$",
                         [("Formel", r"F_G = m \cdot g"),
                          ("Einsetzen", "F_G = " + q(m, "kg") + r" \cdot " + q(g, "N/kg")),
                          ("Ergebnis", "F_G = " + q(F, "N"))],
                         f"Die Gewichtskraft beträgt **{de(F)} N**."))
    if art == "mond":
        F = m * G_MOND
        return dict(
            text=f"{wer} hat eine Masse von **{m} kg**. Wie groß ist die Gewichtskraft auf dem **Mond** "
                 f"(g = 1,62 N/kg)?",
            answer=F, unit="N",
            solution=weg(f"$m = {q(m, 'kg')}$, $g_{{Mond}} = {q(G_MOND, 'N/kg')}$", r"$F_G$ am Mond",
                         [("Formel", r"F_G = m \cdot g_{Mond}"),
                          ("Einsetzen", "F_G = " + q(m, "kg") + r" \cdot " + q(G_MOND, "N/kg")),
                          ("Ergebnis", "F_G = " + q(F, "N"))],
                         f"Am Mond beträgt die Gewichtskraft nur **{de(F)} N** – etwa ein Sechstel wie auf der Erde.",
                         "Die MASSE bleibt aber gleich: " + str(m) + " kg!"))
    if art == "rueck":
        F = m * g
        return dict(
            text=f"Auf der Erde wirkt auf {wer.lower().replace('ein ', 'einen ').replace('eine ', 'eine ')} "
                 f"eine Gewichtskraft von **{de(F)} N**. Wie groß ist die Masse?",
            answer=m, unit="kg",
            solution=weg(f"$F_G = {q(F, 'N')}$, $g = {q(g, 'N/kg')}$", "$m$",
                         [("Formel (umgeformt)", r"F_G = m \cdot g \;\Rightarrow\; m = \frac{F_G}{g}"),
                          ("Einsetzen", "m = " + frac(q(F, "N"), q(g, "N/kg"))),
                          ("Ergebnis", "m = " + q(m, "kg"))],
                         f"Die Masse beträgt **{m} kg**."))
    return dict(
        text=f"Fangfrage: {wer} hat auf der Erde eine Masse von **{m} kg**. "
             f"Wie groß ist die **Masse** auf dem **Mond**?",
        answer=m, unit="kg",
        solution=f"Die Masse ist überall gleich – es ist ja gleich viel 'Stoff'! Also **{m} kg**.  \n"
                 f"Nur die **Gewichtskraft** ändert sich (Erde: {de(m * g)} N, Mond: {de(m * G_MOND)} N).")


def gen_fall(g):
    art = random.choice(["zeit", "tiefe", "speed", "zeit"])
    if art == "zeit":
        name, h = random.choice([("Ein Apfel fällt aus", 5), ("Ein Stein fällt von einer Brücke aus", 20),
                                 ("Eine Kugel fällt vom Schiefen Turm von Pisa aus", 56),
                                 ("Ein Ball fällt aus", 45), ("Ein Schlüssel fällt aus", 10),
                                 ("Eine Münze fällt vom Stephansdom aus", 136)])
        t = math.sqrt(2 * h / g)
        return dict(
            text=f"{name} **{h} m** Höhe. Wie lange dauert der Fall? (Luftwiderstand vernachlässigen, g = {de(g)} m/s²)",
            answer=t, unit="s", tol=max(0.03 * t, 0.06),
            solution=weg(f"$s = {q(h, 'm')}$, $g = {q(g, 'm/s²')}$", "$t$",
                         [("Formel", r"s = \frac{g \cdot t^2}{2}"),
                          ("Umformen", r"t = \sqrt{\frac{2 \cdot s}{g}}"),
                          ("Einsetzen", r"t = \sqrt{" + frac(r"2 \cdot " + q(h, "m"), q(g, "m/s²")) + "}"),
                          ("Rechnen", r"t = \sqrt{" + tx(2 * h / g, 3) + r"\,\text{s}^2}"),
                          ("Ergebnis", "t \\approx " + q(t, "s"))],
                         f"Der Fall dauert etwa **{de(t)} s**."))
    if art == "tiefe":
        t = random.choice([1, 1.5, 2, 2.5, 3, 4, 5])
        h = g * t * t / 2
        return dict(
            text=f"Du lässt einen Stein in einen Brunnen fallen und hörst ihn nach **{de(t)} s** aufklatschen. "
                 f"Wie tief ist der Brunnen? (Die Zeit, die der Schall nach oben braucht, wird vernachlässigt.)",
            answer=h, unit="m",
            solution=weg(f"$t = {q(t, 's')}$, $g = {q(g, 'm/s²')}$", "$s$ (Tiefe)",
                         [("Formel", r"s = \frac{g \cdot t^2}{2}"),
                          ("Einsetzen", "s = " + frac(q(g, "m/s²") + r" \cdot (" + q(t, "s") + ")^2", "2")),
                          ("Rechnen", "s = " + frac(tx(g) + r" \cdot " + tx(t * t), "2") + r"\,\text{m}"),
                          ("Ergebnis", "s \\approx " + q(h, "m"))],
                         f"Der Brunnen ist etwa **{de(h, 1)} m** tief."))
    t = random.choice([1, 2, 3, 4, 5])
    v = g * t
    return dict(
        text=f"Ein Stein fällt frei herunter. Wie schnell ist er nach **{t} s** (in m/s)?",
        answer=v, unit="m/s",
        solution=weg(f"$t = {q(t, 's')}$, $g = {q(g, 'm/s²')}$", "$v$",
                     [("Formel", r"v = g \cdot t"),
                      ("Einsetzen", "v = " + q(g, "m/s²") + r" \cdot " + q(t, "s")),
                      ("Ergebnis", "v = " + q(v, "m/s"))],
                     f"Er ist **{de(v)} m/s** schnell (= {de(v * 3.6, 0)} km/h)."))


def gen_newton(g=None):
    if random.random() < 0.5:
        m = random.choice([2, 5, 10, 20, 50, 100])
        a = random.choice([1, 2, 3, 4, 5])
        F = m * a
        return dict(
            text=f"Ein Wagen mit **{m} kg** wird mit einer Kraft von **{F} N** angeschoben "
                 f"(ohne Reibung). Wie groß ist die Beschleunigung?",
            answer=a, unit="m/s²",
            solution=weg(f"$m = {q(m, 'kg')}$, $F = {q(F, 'N')}$", "$a$",
                         [("Formel (2. Newton'sches Gesetz)", r"F = m \cdot a \;\Rightarrow\; a = \frac{F}{m}"),
                          ("Einsetzen", "a = " + frac(q(F, "N"), q(m, "kg"))),
                          ("Ergebnis", "a = " + q(a, "m/s²"))],
                         f"Die Beschleunigung beträgt **{a} m/s²**."))
    m = random.choice([1000, 1200, 1500, 60, 80])
    a = random.choice([1, 2, 3])
    F = m * a
    return dict(
        text=f"Ein Körper mit **{m} kg** soll mit **{a} m/s²** beschleunigt werden. Welche Kraft ist nötig?",
        answer=F, unit="N",
        solution=weg(f"$m = {q(m, 'kg')}$, $a = {q(a, 'm/s²')}$", "$F$",
                     [("Formel", r"F = m \cdot a"),
                      ("Einsetzen", "F = " + q(m, "kg") + r" \cdot " + q(a, "m/s²")),
                      ("Ergebnis", "F = " + q(F, "N"))],
                     f"Es braucht **{F} N**."))


# =====================================================================
# Sidebar
# =====================================================================
for k in ("punkte", "versuche"):
    st.session_state.setdefault(k, 0)

SEITEN = [
    "Start & Formelblatt",
    "1. Geschwindigkeit (v = s/t)",
    "2. Gleichförmig & beschleunigt",
    "3. Trägheit & Masse",
    "4. Kraft & Gewichtskraft",
    "5. Reibung",
    "6. Newton'sche Gesetze",
    "7. Freier Fall",
    "Prüfungs-Mix",
]
with st.sidebar:
    st.title("Physik-Trainer")
    seite = st.radio("Thema wählen", SEITEN, label_visibility="collapsed")
    st.divider()
    g_wahl = st.radio("Erdbeschleunigung g", ["9,81 m/s² (genau)", "10 m/s² (gerundet)"],
                      help="Frag deine Lehrerin/deinen Lehrer, womit ihr rechnen sollt!")
    G = 9.81 if g_wahl.startswith("9") else 10.0
    st.divider()
    score_platz = st.empty()


def gk(name):
    """Session-Key abhängig von g – bei Wechsel von g gibt es neue Aufgaben."""
    return f"{name}_{G}"


# =====================================================================
# Seiten
# =====================================================================
def seite_start():
    st.title("Physik-Trainer für die Schularbeit")
    st.markdown(
        "Links wählst du ein Thema. Auf jeder Seite gibt es:\n"
        "- **Erklärung** in einfachen Worten\n"
        "- **Schieberegler** zum Ausprobieren – schau, was passiert, wenn du etwas veränderst!\n"
        "- **Übungsaufgaben** mit Knopf zum Prüfen und dem **Lösungsweg**\n"
    )
    st.info(
        "**So löst du jede Rechenaufgabe – immer in 5 Schritten:**\n\n"
        "1. **Gegeben:** Was weiß ich? (Zahlen + Einheiten herausschreiben)\n"
        "2. **Gesucht:** Was will ich wissen?\n"
        "3. **Formel:** Welche Formel verbindet Gegeben und Gesucht?\n"
        "4. **Einsetzen:** Zahlen MIT Einheiten einsetzen\n"
        "5. **Antwort:** Ergebnis mit Einheit + Antwortsatz"
    )
    st.subheader("Formelblatt")
    st.markdown(
        r"""
| Thema | Formel | Was bedeutet das? |
|---|---|---|
| Geschwindigkeit | $v = \dfrac{s}{t}$ | v = Geschwindigkeit, s = Weg, t = Zeit |
| ... umgeformt | $s = v \cdot t \qquad t = \dfrac{s}{v}$ | Formel-Dreieck! |
| Umrechnen | m/s $\xrightarrow{\cdot 3{,}6}$ km/h  und  km/h $\xrightarrow{: 3{,}6}$ m/s | |
| Beschleunigung | $v = a \cdot t$ | a in m/s² (wird jede Sekunde um a m/s schneller) |
| Weg beim Beschleunigen | $s = \dfrac{a \cdot t^2}{2}$ | startet aus dem Stand |
| Freier Fall | $s = \dfrac{g \cdot t^2}{2} \qquad t = \sqrt{\dfrac{2 \cdot s}{g}} \qquad v = g \cdot t$ | g = 9,81 m/s² auf der Erde |
| Gewichtskraft | $F_G = m \cdot g$ | Erde: g = 9,81 N/kg, Mond: g = 1,62 N/kg |
| 2. Newton'sches Gesetz | $F = m \cdot a$ | mehr Kraft → mehr Beschleunigung |
| Masse | 1 t = 1000 kg, 1 kg = 100 dag = 1000 g, 1 dag = 10 g | |
"""
    )
    st.subheader("Das Formel-Dreieck")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(
            """
<svg viewBox="0 0 220 190" width="220">
  <polygon points="110,10 210,180 10,180" fill="#e8f1fb" stroke="#1f77b4" stroke-width="4"/>
  <line x1="60" y1="95" x2="160" y2="95" stroke="#1f77b4" stroke-width="3"/>
  <line x1="110" y1="95" x2="110" y2="180" stroke="#1f77b4" stroke-width="3"/>
  <text x="110" y="78" font-size="38" text-anchor="middle" fill="#d62728" font-weight="bold">s</text>
  <text x="70" y="155" font-size="38" text-anchor="middle" fill="#2ca02c" font-weight="bold">v</text>
  <text x="150" y="155" font-size="38" text-anchor="middle" fill="#ff7f0e" font-weight="bold">t</text>
</svg>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            "Halte mit dem Finger zu, was du **suchst** – der Rest zeigt dir die Formel:\n\n"
            "- **s** zuhalten → v **·** t (nebeneinander = mal)\n"
            "- **v** zuhalten → s **/** t (übereinander = durch)\n"
            "- **t** zuhalten → s **/** v\n\n"
            "Das gleiche Dreieck funktioniert auch für **F = m · g** (F oben, m und g unten)."
        )


def seite_geschwindigkeit():
    st.title("1. Bewegung & Geschwindigkeit")
    einfach(
        "Zwei Leute sprinten 100 m. Die eine braucht 13 s, der andere 16 s. Wer schneller ist, ist "
        "offensichtlich: **gleicher Weg, weniger Zeit**. Genauso offensichtlich ist es, wenn beide 10 Minuten "
        "mit dem Scooter fahren und eine weiter kommt: **gleiche Zeit, mehr Weg**.\n\n"
        "Schwierig wird es erst, wenn **beides verschieden** ist: 300 m in 40 s oder 500 m in 75 s? "
        "Um das fair zu vergleichen, rechnet man aus, **wie viel Weg auf eine einzige Sekunde kommt**. "
        "Genau das ist die Geschwindigkeit – und deshalb **Weg durch Zeit**. "
        "Das Prinzip kennst du vom Preis pro Kilo im Supermarkt.\n\n"
        "**m/s und km/h** messen dasselbe, nur in verschiedenen Einheiten – so wie Meter und Zentimeter. "
        "Die Zahl in km/h ist immer rund 3½-mal größer. 50 km/h klingt nach viel, sind aber „nur“ knapp 14 m/s."
    )
    bauchgefuehl(
        "- Gehen: ca. 1,5 m/s (≈ 5 km/h)\n"
        "- Rad oder Scooter: ca. 5 m/s (≈ 18 km/h)\n"
        "- Auto im Ort: ca. 14 m/s (= 50 km/h)\n"
        "- Autobahn: ca. 36 m/s (≈ 130 km/h)\n\n"
        "Wenn bei dir ein Fußgänger mit 50 m/s unterwegs ist, hast du dich irgendwo verrechnet."
    )
    st.markdown(
        "Die **Geschwindigkeit** sagt, **wie viel Weg** man **in einer bestimmten Zeit** schafft.  \n"
        "Wer in derselben Zeit mehr Weg schafft, ist schneller."
    )
    st.latex(r"v = \frac{s}{t} \qquad \text{Geschwindigkeit} = \frac{\text{Weg}}{\text{Zeit}}")

    tab1, tab2, tab3 = st.tabs(["Rechner", "m/s ↔ km/h", "Üben"])

    with tab1:
        gesucht = st.radio("Was willst du ausrechnen?", ["Geschwindigkeit v", "Weg s", "Zeit t"],
                           horizontal=True)
        c1, c2 = st.columns(2)
        if gesucht == "Geschwindigkeit v":
            s = c1.number_input("Weg s (m)", 0.0, 100000.0, 100.0, 10.0)
            t = c2.number_input("Zeit t (s)", 0.1, 100000.0, 20.0, 1.0)
            v = s / t
            st.markdown(weg(f"$s = {q(s, 'm')}$, $t = {q(t, 's')}$", "$v$",
                            [("Formel", r"v = \frac{s}{t}"),
                             ("Einsetzen", "v = " + frac(q(s, "m"), q(t, "s"))),
                             ("Ergebnis", "v = " + q(v, "m/s") + r" = " + q(v * 3.6, "km/h"))],
                            f"**{de(v)} m/s** bzw. **{de(v * 3.6)} km/h**"))
        elif gesucht == "Weg s":
            v = c1.number_input("Geschwindigkeit v (m/s)", 0.0, 1000.0, 5.0, 0.5)
            t = c2.number_input("Zeit t (s)", 0.0, 100000.0, 60.0, 1.0)
            s = v * t
            st.markdown(weg(f"$v = {q(v, 'm/s')}$, $t = {q(t, 's')}$", "$s$",
                            [("Formel", r"s = v \cdot t"),
                             ("Einsetzen", "s = " + q(v, "m/s") + r" \cdot " + q(t, "s")),
                             ("Ergebnis", "s = " + q(s, "m"))], f"**{de(s)} m**"))
        else:
            s = c1.number_input("Weg s (m)", 0.0, 100000.0, 400.0, 10.0)
            v = c2.number_input("Geschwindigkeit v (m/s)", 0.1, 1000.0, 8.0, 0.5)
            t = s / v
            st.markdown(weg(f"$s = {q(s, 'm')}$, $v = {q(v, 'm/s')}$", "$t$",
                            [("Formel", r"t = \frac{s}{v}"),
                             ("Einsetzen", "t = " + frac(q(s, "m"), q(v, "m/s"))),
                             ("Ergebnis", "t = " + q(t, "s"))], f"**{de(t)} s**"))

    with tab2:
        st.markdown("#### Warum genau 3,6?")
        st.markdown(
            "Wer **1 m/s** fährt, schafft jede Sekunde 1 Meter.  \n"
            "Eine Stunde hat **3600 Sekunden** → in einer Stunde also **3600 m = 3,6 km**.  \n"
            "Also: **1 m/s = 3,6 km/h**."
        )
        st.success("**m/s → km/h: mal 3,6** (Zahl wird größer)   |   **km/h → m/s: durch 3,6** (Zahl wird kleiner)")
        c1, c2 = st.columns(2)
        with c1:
            ms = st.number_input("Geschwindigkeit in m/s", 0.0, 1000.0, 10.0, 0.5)
            st.markdown(f"### {de(ms)} m/s · 3,6 = **{de(ms * 3.6)} km/h**")
        with c2:
            kmh = st.number_input("Geschwindigkeit in km/h", 0.0, 5000.0, 50.0, 1.0)
            st.markdown(f"### {de(kmh)} km/h : 3,6 = **{de(kmh / 3.6)} m/s**")

        st.markdown("#### Wie schnell ist was?")
        bsp = [("Schnecke", 0.001), ("Fußgänger", 1.4), ("Sprinter (Usain Bolt)", 10.4),
               ("Radfahrer", 5.5), ("Auto im Ort", 50 / 3.6), ("Gepard", 30),
               ("Railjet", 230 / 3.6), ("Schall", 340)]
        bsp.sort(key=lambda b: b[1])
        fig = go.Figure(go.Bar(
            y=[b[0] for b in bsp], x=[b[1] for b in bsp], orientation="h", marker_color=BLAU,
            text=[f"{de(b[1], 1)} m/s = {de(b[1] * 3.6, 0)} km/h" for b in bsp], textposition="outside"))
        layout(fig, "Geschwindigkeit in m/s (logarithmische Skala)", "", 380)
        fig.update_xaxes(type="log", range=[-3.5, 3.6])
        zeige(fig)

    with tab3:
        aufgabe(gk("a_v"), lambda: gen_geschwindigkeit(G), "Aufgabe: v = s/t")
        aufgabe(gk("a_um"), lambda: gen_umrechnen(G), "Aufgabe: Umrechnen")


def rennen_fig(v, a, T=10.0):
    dt = 0.1
    ts = np.arange(0, T + dt / 2, dt)
    xa = v * ts
    xb = a * ts ** 2 / 2
    xmax = max(xa.max(), xb.max()) * 1.08 + 1

    def daten(i):
        return [
            go.Scatter(x=[xa[i]], y=[1], mode="markers+text", text=["Fahrrad (gleichförmig)"],
                       textposition="top center", marker=dict(size=24, color=BLAU)),
            go.Scatter(x=[xb[i]], y=[0], mode="markers+text", text=["Auto (beschleunigt)"],
                       textposition="top center", marker=dict(size=24, color=ROT)),
        ]

    frames = [go.Frame(data=daten(i), name=str(i),
                       layout=go.Layout(title_text=f"t = {de(ts[i], 1)} s   |   Fahrrad: {de(xa[i], 0)} m   "
                                                   f"Auto: {de(xb[i], 0)} m"))
              for i in range(len(ts))]
    fig = go.Figure(data=daten(0), frames=frames)
    fig.update_layout(
        height=300, showlegend=False, title="t = 0 s – drück auf ▶ Start",
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis=dict(range=[0, xmax], title="Weg s in m"),
        yaxis=dict(range=[-0.6, 1.8], visible=False),
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=1.25, xanchor="left", direction="left",
                          buttons=[
                              dict(label="▶ Start", method="animate",
                                   args=[None, dict(frame=dict(duration=100, redraw=True),
                                                    transition=dict(duration=0), fromcurrent=False)]),
                              dict(label="Stopp", method="animate",
                                   args=[[None], dict(frame=dict(duration=0, redraw=False),
                                                      mode="immediate")])])],
    )
    return fig


def seite_bewegung():
    st.title("2. Gleichförmige & beschleunigte Bewegung")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Gleichförmig", "Beschleunigt", "Erdbeschleunigung g", "Wettrennen", "Üben"])

    with tab1:
        einfach(
            "Ein Auto mit Tempomat auf der Autobahn: Der Tacho steht die ganze Zeit auf 130 km/h. "
            "Das ist eine **gleichförmige Bewegung** – jede Sekunde kommt **exakt gleich viel Weg** dazu.\n\n"
            "Ein Diagramm ist im Grunde ein **Replay** der Bewegung. Das s-t-Diagramm zeigt, "
            "wie weit jemand zu jedem Zeitpunkt schon gekommen ist:\n"
            "- **steile** Linie → in kurzer Zeit viel Weg → schnell\n"
            "- **flache** Linie → langsam\n"
            "- **waagrechte** Linie → der Weg wächst nicht → steht still\n\n"
            "Das v-t-Diagramm ist einfach der **Tacho über die Zeit aufgezeichnet**. "
            "Tacho bleibt gleich → Linie bleibt waagrecht."
        )
        st.markdown(
            "**Gleichförmige Bewegung** = die Geschwindigkeit bleibt **immer gleich** (keine Beschleunigung).  \n"
            "In jeder Sekunde wird **gleich viel Weg** zurückgelegt."
        )
        c1, c2 = st.columns(2)
        v1 = c1.slider("Geschwindigkeit von A (m/s)", 0.0, 20.0, 5.0, 0.5)
        zwei = c2.checkbox("Zweites Objekt B zum Vergleich", value=True)
        v2 = c2.slider("Geschwindigkeit von B (m/s)", 0.0, 20.0, 10.0, 0.5, disabled=not zwei)
        t = np.linspace(0, 10, 101)
        f1 = go.Figure()
        f1.add_trace(go.Scatter(x=t, y=v1 * t, name=f"A: {de(v1)} m/s", line=dict(color=BLAU, width=3)))
        if zwei:
            f1.add_trace(go.Scatter(x=t, y=v2 * t, name=f"B: {de(v2)} m/s", line=dict(color=ROT, width=3)))
        layout(f1, "Zeit t in s", "Weg s in m", 330, "s-t-Diagramm (Weg-Zeit)")
        f2 = go.Figure()
        f2.add_trace(go.Scatter(x=t, y=v1 * np.ones_like(t), name="A", fill="tozeroy",
                                line=dict(color=BLAU, width=3)))
        if zwei:
            f2.add_trace(go.Scatter(x=t, y=v2 * np.ones_like(t), name="B", line=dict(color=ROT, width=3)))
        layout(f2, "Zeit t in s", "Geschwindigkeit v in m/s", 330, "v-t-Diagramm (Geschwindigkeit-Zeit)")
        f2.update_yaxes(range=[0, 21])
        c1, c2 = st.columns(2)
        with c1:
            zeige(f1)
        with c2:
            zeige(f2)
        st.success(
            "**So erkennst du gleichförmige Bewegung in Diagrammen:**\n\n"
            "- **s-t-Diagramm:** eine **gerade, schräge Linie** durch den Nullpunkt. "
            "**Je steiler, desto schneller.** Waagrechte Linie = steht still.\n"
            "- **v-t-Diagramm:** eine **waagrechte Linie** – die Geschwindigkeit ändert sich nicht. "
            "Je höher die Linie, desto schneller."
        )
        with st.expander("Bonus für Profis: Die Fläche im v-t-Diagramm"):
            st.markdown(f"Die blaue Fläche unter der Linie ist ein Rechteck: "
                        f"Höhe · Breite = {de(v1)} m/s · 10 s = **{de(v1 * 10)} m**. "
                        f"Das ist genau der Weg nach 10 s – vergleiche mit dem s-t-Diagramm!")

    with tab2:
        einfach(
            "Ein Auto steht an der Ampel, Grün, Vollgas. Der Tacho klettert: 0, 10, 20, 30 … Das ist "
            "**Beschleunigung** – und die Zahl a sagt, **wie schnell der Tacho hochzählt**.\n\n"
            "Bei a = 2 m/s² kommen **jede Sekunde 2 m/s dazu**: 0 → 2 → 4 → 6 → 8 …  \n"
            "Deshalb die seltsame Einheit m/s²: Sie bedeutet „m/s **pro Sekunde**“.\n\n"
            "Spannend ist der **Weg**: Er wächst nicht gleichmäßig, sondern explodiert regelrecht. "
            "Der Grund: Du bist **länger unterwegs** und gleichzeitig **immer schneller**. Zwei Effekte, "
            "die sich multiplizieren. Doppelt so lange Gas geben heißt deshalb nicht doppelt, "
            "sondern **viermal so viel Weg**. Daher kommt das t² in der Formel."
        )
        st.markdown(
            "**Beschleunigte Bewegung** = man wird **immer schneller**.  \n"
            "Die **Beschleunigung a** (in m/s²) sagt: **um wie viel m/s wird man jede Sekunde schneller?**  \n"
            "Beispiel: a = 2 m/s² → nach 1 s: 2 m/s, nach 2 s: 4 m/s, nach 3 s: 6 m/s …"
        )
        c1, c2 = st.columns(2)
        with c1:
            st.latex(r"v = a \cdot t")
        with c2:
            st.latex(r"s = \frac{a \cdot t^2}{2}")
        a = st.slider("Beschleunigung a (m/s²)", 0.5, 10.0, 2.0, 0.5)
        t = np.linspace(0, 10, 101)
        f1 = go.Figure(go.Scatter(x=t, y=a * t, line=dict(color=ROT, width=3), name="v"))
        layout(f1, "Zeit t in s", "Geschwindigkeit v in m/s", 330, "v-t-Diagramm: gerade, schräge Linie")
        f2 = go.Figure(go.Scatter(x=t, y=a * t ** 2 / 2, line=dict(color=ROT, width=3), name="s"))
        layout(f2, "Zeit t in s", "Weg s in m", 330, "s-t-Diagramm: Kurve (Parabel), wird immer steiler")
        c1, c2 = st.columns(2)
        with c1:
            zeige(f1)
        with c2:
            zeige(f2)
        st.markdown("##### Wertetabelle")
        ts = list(range(0, 7))
        st.dataframe(
            {"Zeit t (s)": ts,
             "Geschwindigkeit v = a·t (m/s)": [de(a * x) for x in ts],
             "Weg s = a·t²/2 (m)": [de(a * x * x / 2) for x in ts],
             "t² (Quadratzahl)": [x * x for x in ts]},
            hide_index=True, width="stretch")
        st.info("Schau dir die Spalte **Weg** an: nach 2 s ist der Weg **4-mal** so groß wie nach 1 s, "
                "nach 3 s **9-mal** so groß. Das kommt vom **t²** in der Formel!")
        st.markdown(
            "**Vergleich der Diagramme:**\n\n"
            "| | gleichförmig | beschleunigt |\n|---|---|---|\n"
            "| **s-t-Diagramm** | gerade schräge Linie | Kurve, die immer steiler wird |\n"
            "| **v-t-Diagramm** | waagrechte Linie | gerade schräge Linie |"
        )

    with tab3:
        st.markdown(
            f"Alles, was auf der Erde **frei fällt**, wird beschleunigt – mit der **Erdbeschleunigung**  \n"
            f"### g = 9,81 m/s² ≈ 10 m/s²\n"
            f"Ein fallender Stein wird also **jede Sekunde um etwa 10 m/s (≈ 35 km/h) schneller!**"
        )
        ts = list(range(0, 6))
        st.dataframe(
            {"Fallzeit (s)": ts,
             "Geschwindigkeit (m/s)": [de(G * x) for x in ts],
             "Geschwindigkeit (km/h)": [de(G * x * 3.6, 0) for x in ts],
             "Fallstrecke (m)": [de(G * x * x / 2, 1) for x in ts]},
            hide_index=True, width="stretch")
        st.markdown("##### g auf anderen Himmelskörpern")
        orte = [("Mond", 1.62), ("Mars", 3.71), ("Erde", 9.81), ("Jupiter", 24.79)]
        fig = go.Figure(go.Bar(x=[o[0] for o in orte], y=[o[1] for o in orte],
                               text=[f"{de(o[1])} m/s²" for o in orte], textposition="outside",
                               marker_color=["#999", ORANGE, BLAU, "#b5835a"]))
        layout(fig, "", "g in m/s²", 300)
        fig.update_yaxes(range=[0, 29])
        zeige(fig)
        st.markdown("Mehr dazu auf den Seiten **Kraft & Gewichtskraft** und **Freier Fall**.")

    with tab4:
        st.markdown("Ein Fahrrad fährt mit **konstanter** Geschwindigkeit. "
                    "Ein Auto startet gleichzeitig aus dem **Stand** und **beschleunigt**. Wer gewinnt?")
        c1, c2 = st.columns(2)
        v = c1.slider("Geschwindigkeit Fahrrad (m/s)", 1.0, 15.0, 8.0, 0.5)
        a = c2.slider("Beschleunigung Auto (m/s²)", 0.5, 6.0, 2.0, 0.5)
        zeige(rennen_fig(v, a))
        t_treff = 2 * v / a
        if t_treff <= 10:
            st.info(f"Am Anfang ist das Fahrrad vorne, weil das Auto erst Schwung holen muss. "
                    f"Nach **{de(t_treff, 1)} s** überholt das Auto das Fahrrad – "
                    f"denn das Auto wird immer schneller, das Fahrrad nicht.")
        else:
            st.info(f"In 10 s schafft es das Auto nicht, das Fahrrad einzuholen – erst nach {de(t_treff, 1)} s.")

    with tab5:
        aufgabe(gk("a_be"), lambda: gen_beschleunigung(G), "Aufgabe: Beschleunigung")
        aufgabe(gk("a_dia"), lambda: gen_diagramm(G), "Aufgabe: Diagramm lesen")


def seite_traegheit():
    st.title("3. Trägheit & Masse")
    tab1, tab2, tab3 = st.tabs(["Trägheit", "kg – dag – g", "Üben"])

    with tab1:
        einfach(
            "Dinge sind **stur**. Sie machen weiter, was sie gerade machen, bis etwas sie zwingt, "
            "damit aufzuhören:\n"
            "- Ein liegender Ball bleibt liegen, bis ihn jemand anstößt.\n"
            "- Ein rollender Ball würde ewig weiterrollen, wenn ihn nichts bremsen würde.\n\n"
            "Wie stur ein Ding ist, hängt an seiner **Masse**. Einen Fußball kickst du locker weg. "
            "Gib einer Bowlingkugel denselben Kick und dein Fuß verliert (bitte nicht testen). "
            "**Mehr Masse = mehr Trägheit.**\n\n"
            "Und **Masse** ist schlicht: **wie viel Material in einem Ding steckt**. Voller Rucksack, mehr Masse, "
            "mehr Trägheit."
        )
        st.markdown(
            "### Was ist Trägheit?\n"
            "Jeder Körper will **so bleiben, wie er gerade ist**.\n"
            "- Liegt er still → er **will liegen bleiben**.\n"
            "- Bewegt er sich → er **will sich weiterbewegen** (gleich schnell, gleiche Richtung).\n\n"
            "### Je größer die Masse, desto größer die Trägheit!\n"
            "Ein **voller** Einkaufswagen ist schwerer anzuschieben **und** schwerer zu stoppen als ein leerer."
        )
        m = st.slider("Wie voll ist der Einkaufswagen? (Masse in kg)", 10, 150, 20, 5)
        st.progress(m / 150, text=f"Trägheit bei {m} kg")
        if m < 40:
            st.write("Leicht anzuschieben, schnell gestoppt.")
        elif m < 90:
            st.write("Merklich träger – zum Anschieben und Bremsen braucht es schon Kraft.")
        else:
            st.write("Sehr träge: Kommt schwer in Gang und ist schwer wieder zu stoppen.")

        dinge = [("Fußball", 0.43), ("Bowlingkugel", 7), ("Mensch", 60), ("Auto", 1300),
                 ("LKW", 40000)]
        fig = go.Figure(go.Bar(x=[d[0] for d in dinge], y=[d[1] for d in dinge], marker_color=BLAU,
                               text=[f"{de(d[1])} kg" for d in dinge], textposition="outside"))
        layout(fig, "", "Masse in kg (logarithmisch)", 320, "Mehr Masse = mehr Trägheit")
        fig.update_yaxes(type="log", range=[-1, 5.3])
        zeige(fig)

        st.markdown("### Trägheit im Alltag")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                "**Bus bremst plötzlich** → du fällst **nach vorne**. Dein Körper will weiterfahren!\n\n"
                "**Bus fährt los** → du fällst **nach hinten**. Dein Körper will stehen bleiben!\n\n"
                "**Sicherheitsgurt**: Bei einem Unfall würde dein Körper wegen der Trägheit "
                "einfach weiterfliegen – der Gurt hält dich zurück."
            )
        with c2:
            st.markdown(
                "**Tischtuch-Trick**: Zieht man das Tuch blitzschnell weg, bleibt das Geschirr stehen.\n\n"
                "**Hammerstiel**: Man klopft den Stiel unten auf – der Kopf rutscht wegen der Trägheit fester drauf.\n\n"
                "**Experiment für zuhause**: Lege eine Spielkarte auf ein Glas, eine Münze darauf. "
                "Schnipse die Karte weg – die Münze fällt ins Glas!"
            )
        st.warning("Wichtig: Trägheit hängt **nur von der Masse** ab – nicht vom Ort! "
                   "Eine Bowlingkugel ist auch im Weltall (schwerelos) genauso träge wie auf der Erde.")
        quiz("quiz_traeg", [
            ("Ein Bus bremst plötzlich. Wohin bewegen sich die Fahrgäste?",
             ["nach hinten", "nach vorne", "gar nicht", "nach oben"], 1,
             "Die Fahrgäste wollen sich wegen der Trägheit weiterbewegen."),
            ("Welcher Einkaufswagen ist träger?", ["der leere", "der volle", "beide gleich"], 1,
             "Mehr Masse bedeutet mehr Trägheit."),
            ("Ein Bus fährt plötzlich an. Wohin kippen die stehenden Fahrgäste?",
             ["nach vorne", "nach hinten", "zur Seite"], 1,
             "Der Körper will in Ruhe bleiben, der Bus fährt „unter ihm“ weg."),
            ("Ist eine Bowlingkugel im Weltall (schwerelos) träge?",
             ["Nein, ohne Gewicht keine Trägheit", "Ja, genauso träge wie auf der Erde",
              "Nur halb so träge"], 1,
             "Trägheit hängt von der Masse ab, und die Masse ist überall gleich."),
            ("Wozu dient der Sicherheitsgurt?",
             ["Damit man bequemer sitzt",
              "Weil der Körper bei einer Vollbremsung wegen der Trägheit weiterfliegen würde",
              "Damit das Auto schneller bremst"], 1,
             "Der Gurt stoppt deinen Körper, der sich sonst weiterbewegen würde."),
        ])

    with tab2:
        einfach(
            "Ein paar Referenzwerte, damit die Zahlen etwas bedeuten:\n"
            "- **1 g**: eine Büroklammer\n"
            "- **1 dag** (= 10 g): zwei Blatt Papier\n"
            "- **10 dag** (= 100 g): eine Tafel Schokolade\n"
            "- **1 kg**: eine Packung Milch\n"
            "- **1 t**: ein Kleinwagen\n\n"
            "Die Logik beim Umrechnen: **Kleinere Einheit → du brauchst mehr Stück davon → Zahl wird größer.** "
            "Eine Tafel Schokolade ist 1 Tafel, 10 dag oder 100 g – gleiche Schokolade, nur andere Stückelung. "
            "Wie bei Geld: 1 Euro = 100 Cent.",
            "Einfach erklärt – wie schwer ist was?",
        )
        st.markdown("### Einheiten der Masse")
        st.markdown(
            """
<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:1.3em;font-weight:bold;margin:10px 0">
<span style="background:#1f77b4;color:white;padding:10px 16px;border-radius:8px">t</span>
<span>→ · 1000 →</span>
<span style="background:#2c8fd6;color:white;padding:10px 16px;border-radius:8px">kg</span>
<span>→ · 100 →</span>
<span style="background:#4fa8e8;color:white;padding:10px 16px;border-radius:8px">dag</span>
<span>→ · 10 →</span>
<span style="background:#86c5f2;color:#0b2a44;padding:10px 16px;border-radius:8px">g</span>
</div>
<div style="font-size:1.05em">in die andere Richtung (kleine → große Einheit): <b>durch</b> 1000, 100, 10</div>
""",
            unsafe_allow_html=True,
        )
        st.success(
            "**1 kg = 100 dag = 1000 g**  ·  **1 dag = 10 g**  ·  **1 t = 1000 kg**\n\n"
            "**Große Einheit → kleine Einheit: MAL** (die Zahl wird größer)  \n"
            "**Kleine Einheit → große Einheit: DURCH** (die Zahl wird kleiner)"
        )
        st.markdown("*dag* = Dekagramm. Beim Fleischhauer: „10 Deka Wurst“ = 10 dag = 100 g.")

        st.markdown("### Umrechner")
        c1, c2 = st.columns([1, 1])
        wert = c1.number_input("Zahl", 0.0, 1_000_000.0, 1.25, 0.05, format="%.3f")
        einheit = c2.selectbox("Einheit", ["kg", "dag", "g", "t"])
        gramm = wert * MASSE_FAKTOR[einheit]
        cols = st.columns(4)
        for col, e in zip(cols, ["t", "kg", "dag", "g"]):
            col.metric(e, de(gramm / MASSE_FAKTOR[e], 6))
        if abs(gramm - round(gramm)) < 1e-6 and gramm < 1_000_000:
            n = int(round(gramm))
            kg, rest = divmod(n, 1000)
            dag, g_ = divmod(rest, 10)
            st.markdown("##### Stellenwerttafel")
            st.markdown(
                "| kg | dag | g |\n|:-:|:-:|:-:|\n"
                f"| **{kg}** | **{dag:02d}** | **{g_}** |"
            )
            teile = [f"{kg} kg" if kg else "", f"{dag} dag" if dag else "", f"{g_} g" if g_ else ""]
            st.markdown(f"Gemischt geschrieben: **{' '.join(t for t in teile if t) or '0 g'}**")

    with tab3:
        aufgabe("a_masse", gen_masse, "Aufgabe: Masse umrechnen")
        aufgabe("a_masse2", gen_masse, "Noch eine Umrechnung")


def seite_kraft():
    st.title("4. Kraft & Gewichtskraft")
    tab1, tab2, tab3 = st.tabs(["Was ist Kraft?", "Erde und Mond", "Üben"])

    with tab1:
        einfach(
            "**Kraft ist alles, was schiebt, zieht, drückt oder verformt.** Die Kraft selbst sieht man nie, "
            "nur ihre Wirkung: Der Ball fliegt los, die Feder wird länger, die Getränkedose wird zerdrückt.\n\n"
            "**Die Erde zieht permanent an allem**, was auf ihr ist – an dir, am Handy, am Fußball. "
            "Deshalb fällt alles nach unten. Diese Kraft heißt **Gewichtskraft**.\n\n"
            "Der wichtigste Unterschied in diesem Kapitel: **Masse vs. Gewichtskraft.** "
            "Nimm deinen Rucksack mit auf den Mond:\n"
            "- Drin ist **genau dasselbe Zeug** → die **Masse** ändert sich nicht.\n"
            "- Er fühlt sich trotzdem **viel leichter** an, weil der Mond kleiner ist und schwächer zieht → "
            "die **Gewichtskraft** ist nur etwa ein Sechstel.\n\n"
            "Zum Einschätzen: Eine Tafel Schokolade (100 g) drückt mit etwa **1 N** auf deine Hand, "
            "eine Packung Milch (1 kg) mit etwa **10 N**."
        )
        st.markdown(
            "Eine **Kraft** erkennt man an ihrer **Wirkung**:\n"
            "- Sie kann einen Körper **verformen** (Knetmasse drücken, Feder dehnen)\n"
            "- Sie kann die **Bewegung ändern** (anschieben, bremsen, Richtung ändern)\n\n"
            "Die Einheit der Kraft ist **Newton (N)** – benannt nach Isaac Newton.  \n"
            "Kräfte haben immer eine **Richtung** → man zeichnet sie als **Pfeil**.  \n"
            "Gemessen wird sie mit einem **Federkraftmesser**."
        )
        st.markdown(
            "### Die Gewichtskraft (Erdanziehungskraft)\n"
            "Die Erde **zieht alles zu sich hin** – darum fallen Dinge nach unten. "
            "Diese Kraft heißt **Gewichtskraft** $F_G$."
        )
        st.latex(r"F_G = m \cdot g")
        st.markdown(
            "- $m$ = Masse in kg\n"
            "- $g$ = Ortsfaktor: **Erde 9,81 N/kg**, **Mond 1,62 N/kg** (etwa ein Sechstel)"
        )
        st.warning(
            "**Masse ≠ Gewichtskraft!**\n\n"
            "- **Masse** (kg): wie viel „Stoff“ ein Körper hat → ist **überall gleich**.\n"
            "- **Gewichtskraft** (N): wie stark der Planet daran zieht → **hängt vom Ort ab**."
        )

    with tab2:
        m = st.slider("Masse in kg", 1, 150, 45)
        orte = [("Erde", G), ("Mond", G_MOND), ("Mars", 3.71), ("Jupiter", 24.79)]
        cols = st.columns(4)
        for col, (name, gg) in zip(cols, orte):
            col.metric(name, f"{de(m * gg, 1)} N", f"Masse: {m} kg", delta_color="off")
        fig = go.Figure(go.Bar(x=[o[0] for o in orte], y=[m * o[1] for o in orte],
                               marker_color=[BLAU, "#999", ORANGE, "#b5835a"],
                               text=[f"{de(m * o[1], 1)} N" for o in orte], textposition="outside"))
        layout(fig, "", "Gewichtskraft in N", 340, f"Gewichtskraft für {m} kg – die Masse bleibt immer {m} kg!")
        fig.update_yaxes(range=[0, m * 24.79 * 1.2])
        zeige(fig)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Rechnung Erde:**")
            st.latex(f"F_G = {q(m, 'kg')} \\cdot {q(G, 'N/kg')} = {q(m * G, 'N')}")
        with c2:
            st.markdown("**Rechnung Mond:**")
            st.latex(f"F_G = {q(m, 'kg')} \\cdot {q(G_MOND, 'N/kg')} = {q(m * G_MOND, 'N')}")
        st.info(f"Auf dem Mond könntest du etwa **6-mal so hoch springen**, weil der Mond nur ein Sechstel "
                f"so stark zieht. Eine Personenwaage würde dort nur ca. **{de(m * G_MOND / G, 1)} kg** anzeigen "
                f"– sie misst nämlich eigentlich die Kraft!")

    with tab3:
        bauchgefuehl(
            "- Auf der **Erde**: Gewichtskraft in N ≈ **Masse in kg mal 10** (45 kg → ca. 450 N)\n"
            "- Auf dem **Mond**: ungefähr **ein Sechstel** davon (45 kg → ca. 73 N)\n"
            "- Die **Masse** (kg) ändert sich **nie**, egal wo!"
        )
        aufgabe(gk("a_kraft"), lambda: gen_gewicht(G), "Aufgabe: Gewichtskraft")
        aufgabe(gk("a_kraft2"), lambda: gen_gewicht(G), "Noch eine Aufgabe")


UNTERGRUND = {
    "Holzboden": (50, 35, "#d9b77e"),
    "Teppich": (75, 60, "#9b7fb3"),
    "Fliesen": (40, 28, "#cfd8dc"),
    "Eis": (12, 6, "#bfe6ff"),
}
ROLL = 5


def kisten_fig(F, haft, gleit, farbe, rollen):
    grenze = ROLL if rollen else haft
    bewegt = F > grenze
    R = (ROLL if rollen else gleit) if bewegt else F
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-14, x1=12, y0=-1, y1=0, fillcolor=farbe, line_width=0)
    y0 = 0.8 if rollen else 0
    if rollen:
        for x in (-1.3, 1.3):
            fig.add_shape(type="circle", x0=x - 0.4, x1=x + 0.4, y0=0, y1=0.8, fillcolor="#333", line_width=0)
    fig.add_shape(type="rect", x0=-2, x1=2, y0=y0, y1=y0 + 3.5, fillcolor="#c8a165",
                  line=dict(color="#7a5a2b", width=3))
    fig.add_annotation(x=0, y=y0 + 1.75, text="", showarrow=False, font=dict(size=30))
    if F > 0:
        fig.add_annotation(x=-2, y=y0 + 2, ax=-2 - F / 9, ay=y0 + 2, axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowwidth=5, arrowcolor=GRUEN, text="")
        fig.add_annotation(x=-2 - F / 18, y=y0 + 2.7, text="<b>deine Kraft</b>", showarrow=False,
                           font=dict(color=GRUEN, size=14))
    if R > 0:
        fig.add_annotation(x=2 - R / 9, y=0.15, ax=2, ay=0.15, axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowwidth=5, arrowcolor=ROT, text="")
        fig.add_annotation(x=3.5, y=-0.5, text="<b>Reibung</b>", showarrow=False, font=dict(color=ROT, size=14))
    if bewegt:
        for dy in (0.8, 1.8, 2.8):
            fig.add_shape(type="line", x0=2.4, x1=4.0, y0=y0 + dy, y1=y0 + dy,
                          line=dict(color="#888", width=3, dash="dot"))
        fig.add_annotation(x=7.5, y=y0 + 2, text="<b>bewegt sich! </b>", showarrow=False, font=dict(size=16))
    else:
        fig.add_annotation(x=7.5, y=y0 + 2, text="<b>steht still </b>", showarrow=False, font=dict(size=16))
    fig.update_xaxes(visible=False, range=[-14, 12])
    fig.update_yaxes(visible=False, range=[-1, 5.5], scaleanchor="x")
    fig.update_layout(height=260, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor="rgba(0,0,0,0)")
    return fig, bewegt


def seite_reibung():
    st.title("5. Reibung")
    einfach(
        "Keine Oberfläche ist wirklich glatt. Unter dem Mikroskop sieht selbst ein polierter Tisch aus wie "
        "eine **Berglandschaft**. Liegen zwei Oberflächen aufeinander, verhaken sich diese Zacken – "
        "ähnlich wie zwei Bürsten, die man ineinander drückt. Das ist Reibung.\n\n"
        "**Haftreibung** – die Kiste steht, die Zacken sind tief ineinander verkeilt. "
        "Der **erste Ruck** kostet deshalb am meisten Kraft.\n\n"
        "**Gleitreibung** – sobald die Kiste rutscht, springen die Zacken nur noch übereinander "
        "und haben keine Zeit, sich richtig festzuhaken. Weiterschieben ist leichter als Losschieben.\n\n"
        "**Rollreibung** – ein Rad schleift nicht über den Boden, es setzt bei jeder Umdrehung neu auf. "
        "Fast nichts verhakt sich. Darum sind Skateboards, Rollkoffer und Fahrräder so effizient.\n\n"
        "**Selbst testen:** Schieb ein dickes Buch mit einem Finger über den Tisch – der Start ist am "
        "schwersten. Dann zwei runde Stifte drunterlegen und nochmal. Großer Unterschied."
    )
    st.markdown(
        "**Reibung** entsteht, wenn sich zwei Oberflächen berühren. Keine Oberfläche ist ganz glatt – "
        "unter dem Mikroskop sieht man winzige Hügel, die sich **ineinander verhaken**.  \n"
        "Die Reibungskraft wirkt **immer gegen die Bewegung**."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("### Haftreibung\nDer Körper **steht** noch.\nMan muss erst **fest drücken**, "
                        "damit er überhaupt losrutscht.\n\n*Beispiel: schwere Kiste anschieben, "
                        "Auto parkt am Hang.*\n\n**am größten**")
    with c2:
        with st.container(border=True):
            st.markdown("### Gleitreibung\nDer Körper **rutscht** schon.\nDas Weiterschieben geht "
                        "**leichter** als das Losschieben.\n\n*Beispiel: Schlitten, Ski, rutschende "
                        "Kiste, Radiergummi.*\n\n**mittel**")
    with c3:
        with st.container(border=True):
            st.markdown("### Rollreibung\nDer Körper **rollt** auf Rädern oder Kugeln.\n"
                        "Das geht **am allerleichtesten**.\n\n*Beispiel: Fahrrad, Skateboard, "
                        "Rollkoffer, Kugellager.*\n\n**am kleinsten**")
    st.success("### Merke:  Haftreibung  >  Gleitreibung  >  Rollreibung")

    st.markdown("### Experiment: Schieb die Kiste!")
    c1, c2, c3 = st.columns([2, 1, 1])
    F = c1.slider("Wie fest schiebst du?", 0, 100, 30)
    boden = c2.selectbox("Untergrund", list(UNTERGRUND))
    rollen = c3.checkbox("Kiste auf Rollen stellen")
    haft, gleit, farbe = UNTERGRUND[boden]
    fig, bewegt = kisten_fig(F, haft, gleit, farbe, rollen)
    zeige(fig)
    if rollen:
        msg = ("Mit Rollen genügt schon ein kleiner Schubs – **Rollreibung** ist sehr klein!"
               if bewegt else "Auch auf Rollen braucht es einen kleinen Schubs.")
    elif bewegt:
        msg = (f"Du hast die **Haftreibung** überwunden! Jetzt rutscht die Kiste, und es wirkt die "
               f"kleinere **Gleitreibung**. Zum Weiterschieben bräuchtest du nicht mehr so viel Kraft.")
    else:
        msg = (f"Die **Haftreibung** hält genauso stark dagegen, wie du drückst – die Kiste bleibt stehen. "
               f"Drück fester! (Tipp: Auf {boden} brauchst du mehr als {haft})")
    st.info(msg)

    st.markdown("#### So viel Kraft braucht man beim Anschieben einer Kiste")
    t = np.linspace(0, 10, 201)
    kraft = np.where(t < 3, haft * t / 3, np.where(t < 3.4, haft - (haft - gleit) * (t - 3) / 0.4, gleit))
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t, y=kraft, name="Kiste am Boden", line=dict(color=ROT, width=4)))
    fig2.add_trace(go.Scatter(x=t, y=np.minimum(t / 3, 1) * ROLL, name="Kiste auf Rollen",
                              line=dict(color=GRUEN, width=4)))
    fig2.add_annotation(x=3, y=haft, text="Haftreibung überwunden –<br>jetzt rutscht sie!", ax=60, ay=-35)
    fig2.add_annotation(x=7, y=gleit, text="Gleitreibung (weniger)", ax=0, ay=-35)
    fig2.add_annotation(x=7, y=ROLL, text="Rollreibung (ganz wenig)", ax=0, ay=-30)
    layout(fig2, "Zeit", "nötige Kraft", 320)
    fig2.update_xaxes(showticklabels=False)
    fig2.update_yaxes(showticklabels=False, range=[0, 90])
    zeige(fig2)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Reibung ist nützlich")
        st.markdown("- Gehen ohne Ausrutschen (Schuhsohlen mit Profil)\n- Bremsen beim Fahrrad und Auto\n"
                    "- Autoreifen haften auf der Straße\n- Schrauben und Nägel halten\n"
                    "- Streusand im Winter macht die Straße weniger rutschig")
    with c2:
        st.markdown("#### Reibung stört")
        st.markdown("- Maschinenteile nutzen sich ab → **Öl/Schmiermittel**\n"
                    "- Schwere Möbel verschieben → **Rollen** oder Filzgleiter\n"
                    "- Fahrrad wird langsamer → Reifen gut aufpumpen\n"
                    "- Reibung macht **Wärme** (Hände reiben!)")

    quiz("quiz_reib", [
        ("Welche Reibung ist am größten?", ["Rollreibung", "Gleitreibung", "Haftreibung"], 2,
         "Losschieben ist am schwersten: Haftreibung > Gleitreibung > Rollreibung."),
        ("Du schiebst leicht gegen einen schweren Kasten, er bewegt sich nicht. Welche Reibung wirkt?",
         ["Haftreibung", "Gleitreibung", "Rollreibung"], 0, "Der Kasten haftet noch am Boden."),
        ("Welche Reibung wirkt beim Schlittenfahren?", ["Haftreibung", "Gleitreibung", "Rollreibung"], 1,
         "Die Kufen gleiten über den Schnee."),
        ("Warum stellt man schwere Kästen beim Umzug auf Rollbretter?",
         ["Weil Rollreibung am kleinsten ist", "Weil die Kästen dann leichter werden",
          "Weil Haftreibung kleiner als Rollreibung ist"], 0,
         "Rollen ist viel leichter als Schieben. Die Masse ändert sich nicht!"),
        ("Warum ist Glatteis gefährlich?",
         ["Weil Eis kalt ist", "Weil die Reibung zwischen Reifen und Straße sehr klein ist",
          "Weil Autos auf Eis schwerer werden"], 1, "Wenig Reibung → Bremsen und Lenken funktionieren schlecht."),
        ("Wofür ist Reibung nützlich?", ["Bremsen beim Fahrrad", "Abnutzung von Motoren",
                                         "Damit Möbel schwer zu schieben sind"], 0,
         "Ohne Reibung könnten wir weder bremsen noch gehen."),
    ])


NEWTON_SZENEN = [
    ("Eine Rakete stößt heiße Gase nach unten aus und fliegt dadurch nach oben.", 2),
    ("Bei einer Vollbremsung kippen die Fahrgäste nach vorne.", 0),
    ("Ein leerer Einkaufswagen lässt sich mit derselben Kraft schneller beschleunigen als ein voller.", 1),
    ("Ein Eishockey-Puck gleitet auf dem Eis sehr lange geradeaus weiter.", 0),
    ("Du ruderst: Du drückst das Wasser nach hinten, das Boot fährt nach vorne.", 2),
    ("Je fester du gegen den Ball trittst, desto schneller fliegt er weg.", 1),
    ("Du springst vom Skateboard nach vorne ab – das Board rollt nach hinten weg.", 2),
    ("Eine Raumsonde fliegt im Weltall ohne Antrieb jahrelang gleich schnell weiter.", 0),
    ("Ein LKW braucht einen viel stärkeren Motor als ein Moped, um gleich schnell zu beschleunigen.", 1),
    ("Ein Luftballon, den man loslässt, saust davon, weil die Luft nach hinten ausströmt.", 2),
]
NEWTON_OPT = ["1. Trägheitsgesetz", "2. Aktionsprinzip (F = m · a)", "3. Wechselwirkung (actio = reactio)"]


def seite_newton():
    st.title("6. Die drei Newton'schen Gesetze (Axiome)")
    einfach(
        "Isaac Newton hat um 1687 die Regeln aufgeschrieben, nach denen sich alles bewegt – vom Fußball "
        "bis zur Rakete. In einem Satz pro Gesetz:\n\n"
        "**1. Nichts ändert sich von selbst.** Was liegt, bleibt liegen. Was fliegt, fliegt geradeaus "
        "weiter. Nur eine Kraft kann daran etwas ändern. (Das ist die Trägheit von vorhin.)\n\n"
        "**2. Mehr Kraft, mehr Wirkung – mehr Masse, weniger Wirkung.** Ein harter Schuss beschleunigt den "
        "Ball stärker als ein lockerer Pass. Und mit demselben Schuss bewegst du einen Medizinball "
        "kaum vom Fleck.\n\n"
        "**3. Jede Kraft hat eine Gegenkraft.** Steh auf Inlineskates und drück gegen eine Wand – "
        "**du** rollst nach hinten. Die Wand drückt genauso fest zurück, wie du gegen sie drückst. "
        "Raketen funktionieren genau so."
    )
    tab1, tab2, tab3, tab4 = st.tabs(["1. Trägheitsgesetz", "2. Aktionsprinzip", "3. Wechselwirkung",
                                      "Üben"])
    with tab1:
        st.markdown(
            "### 1. Newton'sches Gesetz – Trägheitsgesetz\n"
            "> Ein Körper bleibt **in Ruhe** oder bewegt sich **gleichförmig geradeaus weiter**, "
            "solange **keine Kraft** auf ihn wirkt.\n\n"
            "Das ist genau die **Trägheit**! Ohne Kraft ändert sich die Bewegung nicht.\n\n"
            "- Ein Puck gleitet auf glattem Eis sehr weit (fast keine Reibung).\n"
            "- Raumsonden fliegen im Weltall jahrelang ohne Motor weiter.\n"
            "- Bremst der Bus, fliegst du nach vorne – du willst dich weiterbewegen.\n\n"
            "*Warum bleibt dann ein rollender Ball auf der Wiese stehen?* → Weil doch eine Kraft wirkt: "
            "die **Reibung**!"
        )
    with tab2:
        st.markdown(
            "### 2. Newton'sches Gesetz – Aktionsprinzip\n"
            "> Eine Kraft **ändert die Bewegung** eines Körpers. Je **größer die Kraft**, desto stärker die "
            "Beschleunigung. Je **größer die Masse**, desto schwächer die Beschleunigung."
        )
        st.latex(r"F = m \cdot a \qquad\Rightarrow\qquad a = \frac{F}{m}")
        c1, c2 = st.columns(2)
        F = c1.slider("Kraft F (N)", 0, 500, 100, 10)
        m = c2.slider("Masse m (kg)", 1, 100, 20)
        a = F / m
        st.latex(f"a = {frac(q(F, 'N'), q(m, 'kg'))} = {q(a, 'm/s²')}")
        st.progress(min(a / 50, 1.0), text=f"Beschleunigung: {de(a)} m/s²")
        st.info("Probier's aus: Mach die **Kraft doppelt so groß** → die Beschleunigung verdoppelt sich. "
                "Mach die **Masse doppelt so groß** → die Beschleunigung halbiert sich.")
    with tab3:
        st.markdown(
            "### 3. Newton'sches Gesetz – Wechselwirkung (actio = reactio)\n"
            "> Übt ein Körper A eine Kraft auf Körper B aus, dann übt B eine **gleich große Kraft in die "
            "entgegengesetzte Richtung** auf A aus.\n\n"
            "Kräfte treten **immer paarweise** auf!\n\n"
            "- Rakete drückt Gas nach unten → Gas drückt Rakete nach oben\n"
            "- Beim Schwimmen drückst du das Wasser nach hinten → du kommst nach vorne\n"
            "- Luftballon: Luft strömt nach hinten → Ballon fliegt nach vorne\n"
            "- Beim Gehen drückst du den Boden nach hinten → der Boden schiebt dich nach vorne"
        )
        st.markdown("#### Experiment: Zwei Leute auf Skateboards stoßen sich voneinander ab")
        c1, c2 = st.columns(2)
        m1 = c1.slider("Masse Person A (kg)", 20, 100, 30)
        m2 = c2.slider("Masse Person B (kg)", 20, 100, 60)
        F, dauer = 120, 0.5
        v1, v2 = F * dauer / m1, F * dauer / m2
        fig = go.Figure()
        fig.add_annotation(x=-0.3, y=0, ax=-0.3 - v1, ay=0, axref="x", ayref="y", showarrow=True,
                           arrowhead=3, arrowwidth=6, arrowcolor=BLAU, text="", xref="x", yref="y")
        fig.add_annotation(x=0.3, y=0, ax=0.3 + v2, ay=0, axref="x", ayref="y", showarrow=True,
                           arrowhead=3, arrowwidth=6, arrowcolor=ROT, text="")
        fig.add_annotation(x=-0.3 - v1 - 0.3, y=0, text=f"A ({m1} kg)<br>{de(v1, 1)} m/s",
                           showarrow=False, xanchor="right", font=dict(color=BLAU, size=14))
        fig.add_annotation(x=0.3 + v2 + 0.3, y=0, text=f"B ({m2} kg)<br>{de(v2, 1)} m/s",
                           showarrow=False, xanchor="left", font=dict(color=ROT, size=14))
        fig.add_annotation(x=0, y=0, text="", showarrow=False, font=dict(size=22))
        fig.update_xaxes(visible=False, range=[-6, 6])
        fig.update_yaxes(visible=False, range=[-1, 1])
        fig.update_layout(height=170, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor="rgba(0,0,0,0)")
        zeige(fig)
        st.info("Beide spüren **genau die gleich große Kraft** – nur in entgegengesetzte Richtungen. "
                "Weil die leichtere Person weniger träge ist, rollt es **schneller** weg.")
    with tab4:
        st.markdown("#### Welches Gesetz steckt dahinter?")
        if "newton_auswahl" not in st.session_state:
            st.session_state.newton_auswahl = random.sample(NEWTON_SZENEN, 5)
        if st.button("Neue Beispiele"):
            st.session_state.newton_auswahl = random.sample(NEWTON_SZENEN, 5)
            for i in range(5):
                st.session_state.pop(f"quiz_newton_{i}", None)
        quiz("quiz_newton", [(text, NEWTON_OPT, idx, "") for text, idx in st.session_state.newton_auswahl])
        aufgabe("a_newton", gen_newton, "Aufgabe: F = m · a")


def fall_animation(h, g):
    T = math.sqrt(2 * h / g)
    dt = max(0.05, T / 100)
    ts = np.append(np.arange(0, T, dt), T)
    ys = h - g * ts ** 2 / 2

    def daten(i):
        return [go.Scatter(x=[0.6], y=[ys[i]], mode="markers", marker=dict(size=22, color=ROT))]

    frames = [go.Frame(data=daten(i), name=str(i),
                       layout=go.Layout(title_text=f"t = {de(ts[i], 2)} s   Höhe: {de(max(ys[i], 0), 1)} m   "
                                                   f"v = {de(g * ts[i], 1)} m/s"))
              for i in range(len(ts))]
    fig = go.Figure(data=daten(0), frames=frames)
    fig.add_shape(type="rect", x0=-0.6, x1=0.2, y0=0, y1=h, fillcolor="#e0d6c2", line=dict(color="#a08f6b"))
    fig.add_shape(type="rect", x0=-2, x1=2, y0=-h * 0.04, y1=0, fillcolor="#7cb342", line_width=0)
    fig.update_layout(
        height=480, showlegend=False, title="drück auf ▶ Fallen lassen",
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis=dict(range=[-2, 2], visible=False),
        yaxis=dict(range=[-h * 0.04, h * 1.08], title="Höhe in m"),
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=1.0, xanchor="left", yanchor="top",
                          buttons=[dict(label="▶ Fallen lassen", method="animate",
                                        args=[None, dict(frame=dict(duration=dt * 1000, redraw=True),
                                                         transition=dict(duration=0), fromcurrent=False)])])],
    )
    return fig


def strobo_fig(h, g):
    T = math.sqrt(2 * h / g)
    schritt = next(s for s in (0.1, 0.2, 0.25, 0.5, 1.0, 2.0) if T / s <= 12)
    ts = np.arange(0, T + 1e-9, schritt)
    ys = h - g * ts ** 2 / 2
    fig = go.Figure(go.Scatter(x=np.zeros_like(ts), y=ys, mode="markers+text",
                               marker=dict(size=16, color=ROT),
                               text=[f"  t = {de(t, 2)} s" for t in ts], textposition="middle right"))
    fig.add_shape(type="rect", x0=-2, x1=2, y0=-h * 0.04, y1=0, fillcolor="#7cb342", line_width=0)
    fig.update_layout(height=480, showlegend=False, margin=dict(l=10, r=10, t=45, b=10),
                      title=f"Stroboskop-Bild: alle {de(schritt)} s ein Foto",
                      xaxis=dict(range=[-1, 3], visible=False),
                      yaxis=dict(range=[-h * 0.04, h * 1.08], title="Höhe in m"))
    return fig


def tiefe_mit_schall(t, g, c=SCHALL):
    # t = sqrt(2h/g) + h/c ; u = sqrt(h): u²/c + k·u - t = 0
    k = math.sqrt(2 / g)
    u = (-k + math.sqrt(k * k + 4 * t / c)) / (2 / c)
    return u * u


def seite_fall():
    st.title("7. Freier Fall")
    einfach(
        "Alles, was fällt, wird **jede Sekunde um ca. 35 km/h schneller**. Nach 1 s ist ein Stein "
        "fast so schnell wie ein Moped, nach 3 s so schnell wie ein Auto auf der Freilandstraße (ca. 100 km/h). "
        "Genau das spürst du in einem Free-Fall-Tower im Freizeitpark.\n\n"
        "Weil das Tempo ständig steigt, schafft ein fallender Gegenstand in jeder Sekunde "
        "**mehr Weg als in der davor**:\n"
        "- in der **1.** Sekunde: ca. **5 m**\n"
        "- in der **2.** Sekunde: ca. **15 m** dazu (insgesamt 20 m)\n"
        "- in der **3.** Sekunde: ca. **25 m** dazu (insgesamt 45 m)\n"
        "- in der **4.** Sekunde: ca. **35 m** dazu (insgesamt 80 m)\n\n"
        "Klassischer Denkfehler beim Brunnen: „4 Sekunden mal 5 m = 20 m.“ Falsch – der Stein wird ja immer "
        "schneller. Nach 4 s ist er schon **ca. 80 m** tief.\n\n"
        "Und nein, schwere Dinge fallen **nicht** schneller. Ein großer und ein kleiner Stein kommen "
        "gleichzeitig unten an. Nur sehr leichte, flache Dinge wie Federn oder Papier werden von der "
        "**Luft** ausgebremst."
    )
    bauchgefuehl(
        "Merk dir **5 – 20 – 45 – 80**: So viele Meter fällt etwas nach 1, 2, 3 und 4 Sekunden.\n\n"
        "- Apfel aus **5 m** → ca. **1 s**\n"
        "- Pisa mit **56 m** → liegt zwischen 45 und 80 → also zwischen **3 und 4 s** (genau: ca. 3,4 s)\n"
        "- Brunnen, Platsch nach **4 s** → ca. **80 m** tief"
    )
    st.markdown(
        "Lässt man etwas fallen, wird es durch die Erdanziehung **immer schneller** – "
        f"jede Sekunde um **g = {de(G)} m/s**. Der freie Fall ist also eine **beschleunigte Bewegung** "
        "mit a = g."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.latex(r"s = \frac{g \cdot t^2}{2}")
        st.caption("Höhe aus der Zeit")
    with c2:
        st.latex(r"t = \sqrt{\frac{2 \cdot s}{g}}")
        st.caption("Zeit aus der Höhe")
    with c3:
        st.latex(r"v = g \cdot t")
        st.caption("Geschwindigkeit nach t Sekunden")

    tab1, tab2, tab3, tab4 = st.tabs(["Wie lange fällt es?", "Wie tief ist der Brunnen?",
                                      "Fallen schwere Dinge schneller?", "Üben"])
    with tab1:
        presets = {"Apfel (5 m)": 5, "10-m-Sprungturm": 10, "Schiefer Turm von Pisa (56 m)": 56,
                   "Stephansdom (136 m)": 136, "Eigene Höhe": None}
        wahl = st.radio("Von wo fällt es?", list(presets), horizontal=True)
        h = presets[wahl] if presets[wahl] is not None else st.slider("Höhe in m", 1, 300, 30)
        t = math.sqrt(2 * h / G)
        v = G * t
        c1, c2, c3 = st.columns(3)
        c1.metric("Fallzeit", f"{de(t)} s")
        c2.metric("Aufprall-Geschwindigkeit", f"{de(v, 1)} m/s")
        c3.metric("das sind", f"{de(v * 3.6, 0)} km/h")
        with st.container(border=True):
            st.markdown("**Lösungsweg**")
            st.markdown(weg(f"$s = {q(h, 'm')}$, $g = {q(G, 'm/s²')}$", "Fallzeit $t$ und Geschwindigkeit $v$",
                            [("Formel", r"s = \frac{g \cdot t^2}{2} \;\Rightarrow\; t = \sqrt{\frac{2 \cdot s}{g}}"),
                             ("Einsetzen", r"t = \sqrt{" + frac(r"2 \cdot " + q(h, "m"), q(G, "m/s²")) + r"} = \sqrt{"
                              + tx(2 * h / G, 3) + r"\,\text{s}^2}"),
                             ("Ergebnis", r"t \approx " + q(t, "s")),
                             ("Geschwindigkeit", r"v = g \cdot t = " + q(G, "m/s²") + r" \cdot " + q(t, "s")
                              + r" \approx " + q(v, "m/s", 1))],
                            f"Es fällt etwa **{de(t)} s** lang und trifft mit ca. **{de(v, 1)} m/s** "
                            f"({de(v * 3.6, 0)} km/h) auf."))
        c1, c2 = st.columns(2)
        with c1:
            zeige(fall_animation(h, G))
        with c2:
            zeige(strobo_fig(h, G))
        st.info("Im Stroboskop-Bild werden die **Abstände zwischen den Punkten immer größer** – "
                "der Gegenstand wird also immer schneller!")
        if st.checkbox("Und auf dem Mond?"):
            tm = math.sqrt(2 * h / G_MOND)
            st.markdown(f"Auf dem Mond (g = 1,62 m/s²) würde der Fall aus {h} m **{de(tm)} s** dauern – "
                        f"etwa **{de(tm / t, 1)}-mal so lang** wie auf der Erde.")
        st.markdown("##### Fall-Tabelle")
        ts = list(range(0, 7))
        st.dataframe({"Zeit (s)": ts, "Fallstrecke (m)": [de(G * x * x / 2, 1) for x in ts],
                      "Geschwindigkeit (m/s)": [de(G * x, 1) for x in ts]},
                     hide_index=True, width="stretch")

    with tab2:
        st.markdown("Du lässt einen Stein in einen Brunnen fallen und stoppst die Zeit, bis du es "
                    "**platschen** hörst. Daraus kannst du die **Tiefe** berechnen!")
        t = st.slider("Zeit bis zum Platschen (s)", 0.5, 8.0, 4.0, 0.1)
        h = G * t * t / 2
        st.metric("Tiefe des Brunnens", f"{de(h, 1)} m")
        with st.container(border=True):
            st.markdown("**Lösungsweg**")
            st.markdown(weg(f"$t = {q(t, 's')}$, $g = {q(G, 'm/s²')}$", "Tiefe $s$",
                            [("Formel", r"s = \frac{g \cdot t^2}{2}"),
                             ("Einsetzen", "s = " + frac(q(G, "m/s²") + r" \cdot (" + q(t, "s") + ")^2", "2")),
                             ("Rechnen", "s = " + frac(tx(G) + r" \cdot " + tx(t * t), "2") + r"\,\text{m}"),
                             ("Ergebnis", r"s \approx " + q(h, "m", 1))],
                            f"Der Brunnen ist ungefähr **{de(h, 1)} m** tief."))
        with st.expander("Bonus für Profis: Der Schall braucht auch Zeit!"):
            ht = tiefe_mit_schall(t, G)
            st.markdown(
                f"Der Schall vom Platschen muss erst wieder nach oben – mit ca. **340 m/s**. "
                f"Ein Teil der {de(t, 1)} s ist also gar nicht Fallzeit.  \n"
                f"Genau gerechnet ist der Brunnen nur ca. **{de(ht, 1)} m** tief "
                f"(Fallzeit {de(math.sqrt(2 * ht / G))} s + Schallzeit {de(ht / SCHALL)} s).  \n"
                f"In der Schularbeit wird das meistens **vernachlässigt**."
            )

    with tab3:
        st.markdown(
            "**Fällt eine Bowlingkugel schneller als eine Feder?**\n\n"
            "Im Alltag ja – aber nur wegen des **Luftwiderstands**! Die Feder wird von der Luft gebremst.\n\n"
            "**Ohne Luft (im Vakuum) fallen alle Körper gleich schnell** – egal wie schwer sie sind.\n\n"
            "- Der Legende nach hat **Galileo Galilei** am Schiefen Turm von Pisa Kugeln mit verschiedener "
            "Masse fallen lassen – sie kamen gleichzeitig unten an.\n"
            "- 1971 hat der Astronaut David Scott auf dem **Mond** (dort gibt es keine Luft) einen Hammer und "
            "eine Feder gleichzeitig fallen lassen: Beide landeten **gleichzeitig**!\n\n"
            "Darum kommt in den Formeln für den freien Fall **keine Masse** vor."
        )

    with tab4:
        aufgabe(gk("a_fall"), lambda: gen_fall(G), "Aufgabe: Freier Fall")
        aufgabe(gk("a_fall2"), lambda: gen_fall(G), "Noch eine Aufgabe")


GENS = [gen_geschwindigkeit, gen_umrechnen, gen_beschleunigung, gen_diagramm, gen_masse,
        gen_gewicht, gen_fall, gen_newton]


def seite_mix():
    st.title("Prüfungs-Mix")
    st.markdown("Zufällige Aufgaben aus **allen** Themen – wie bei der Schularbeit. "
                "Rechne zuerst auf einem Zettel (Gegeben – Gesucht – Formel – Einsetzen – Antwort)!")
    aufgabe(gk("a_mix"), lambda: random.choice(GENS)(G), "Mix-Aufgabe")
    if st.button("Punktestand zurücksetzen"):
        st.session_state.punkte = 0
        st.session_state.versuche = 0
        st.rerun()


SEITEN_FN = dict(zip(SEITEN, [seite_start, seite_geschwindigkeit, seite_bewegung, seite_traegheit,
                              seite_kraft, seite_reibung, seite_newton, seite_fall, seite_mix]))
SEITEN_FN[seite]()

with score_platz.container():
    p, v = st.session_state.punkte, st.session_state.versuche
    st.metric("Richtig gelöst", f"{p} von {v}")
    if v:
        st.progress(p / v)
